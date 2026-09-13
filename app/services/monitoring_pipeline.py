import os
import uuid
import json
import datetime
import sqlite3
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from scipy.stats import ks_2samp, chisquare
from statsmodels.stats.multitest import multipletests
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

from app.config import DB_PATH, MONITORING_DIR, EXPECTED_THRESHOLD, PROJECT_ROOT
from app.services.validation import (
    validate_file, validate_schema, compute_data_quality_summary,
    compute_schema_hash, ALL_FEATURES, NUMERICAL_FEATURES, CATEGORICAL_FEATURES,
    TARGET_COLUMN, ID_COLUMN
)

BASELINE_F1 = 0.6357
BASELINE_ACCURACY = 0.7608
BASELINE_PRECISION = 0.5336
BASELINE_RECALL = 0.7861
BASELINE_ROC_AUC = 0.8490

INCOMING_DIR = MONITORING_DIR / "incoming_batches"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_baseline_profile() -> Dict[str, Any]:
    with open(MONITORING_DIR / "baseline_profile_v7.json", "r") as f:
        return json.load(f)


def get_baseline_dataset() -> pd.DataFrame:
    """Reconstructs the frozen V7 baseline train dataset for 2-sample tests."""
    raw_data_path = PROJECT_ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
    raw_df = pd.read_csv(raw_data_path)
    raw_df["TotalCharges"] = pd.to_numeric(raw_df["TotalCharges"], errors="coerce").fillna(0.0)
    
    # Split using the exact V7 random seed and stratified split
    from sklearn.model_selection import train_test_split
    y_raw = raw_df["Churn"].map({"No": 0, "Yes": 1}).astype(int)
    X_raw = raw_df[ALL_FEATURES].copy()
    X_train, _, _, _ = train_test_split(X_raw, y_raw, test_size=0.2, random_state=42, stratify=y_raw)
    return X_train


# ── V7 Drift Methodology ─────────────────────────────────────────────

def run_ks_test(baseline_col, batch_col):
    """Kolmogorov-Smirnov two-sample test for numerical features."""
    b_clean = pd.Series(baseline_col).dropna().values
    cur_clean = pd.Series(batch_col).dropna().values
    stat, p_val = ks_2samp(b_clean, cur_clean)
    return {
        "test": "Kolmogorov-Smirnov",
        "statistic": float(stat),
        "p_value": float(p_val)
    }


def run_chi_square_test(baseline_col, batch_col, baseline_categories):
    """
    Chi-Square goodness-of-fit test for categorical features.
    Expected counts are computed via baseline proportions multiplied by the batch size.
    """
    b_s = pd.Series(baseline_col).dropna()
    cur_s = pd.Series(batch_col).dropna()

    b_counts = b_s.value_counts()
    b_total = len(b_s)
    b_props = {cat: b_counts.get(cat, 0) / b_total for cat in baseline_categories}

    cur_counts = cur_s.value_counts()
    cur_total = len(cur_s)
    cur_props = {}

    observed = []
    expected = []
    cats_used = []

    for cat in baseline_categories:
        exp_count = b_props[cat] * cur_total
        obs_count = cur_counts.get(cat, 0)
        cur_props[cat] = obs_count / cur_total if cur_total > 0 else 0.0

        if exp_count > 0:
            observed.append(obs_count)
            expected.append(exp_count)
            cats_used.append(cat)

    if len(cats_used) < 2:
        return {
            "test": "Chi-Square (insufficient categories)",
            "statistic": 0.0,
            "p_value": 1.0,
            "n_categories": len(baseline_categories),
            "baseline_proportions": b_props,
            "batch_proportions": cur_props,
        }

    chi2_stat, p_val = chisquare(f_obs=observed, f_exp=expected)
    return {
        "test": "Chi-Square",
        "statistic": float(chi2_stat),
        "p_value": float(p_val),
        "n_categories": len(baseline_categories),
        "baseline_proportions": b_props,
        "batch_proportions": cur_props,
    }


def compute_tvd(baseline_props, batch_props):
    """Total Variation Distance: 0.5 * sum(|p_baseline - p_batch|)."""
    all_cats = set(list(baseline_props.keys()) + list(batch_props.keys()))
    tvd = 0.0
    for cat in all_cats:
        p_base = baseline_props.get(cat, 0.0)
        p_batch = batch_props.get(cat, 0.0)
        tvd += abs(p_base - p_batch)
    return float(tvd / 2.0)


def detect_drift(baseline_df: pd.DataFrame, batch_df: pd.DataFrame,
                 baseline_profile: Dict[str, Any], alpha: float = 0.05) -> pd.DataFrame:
    """Executes V7 drift detection across all 19 monitored features."""
    results = []

    # 1. Numerical: KS test
    for feat in NUMERICAL_FEATURES:
        ks = run_ks_test(baseline_df[feat], batch_df[feat])
        results.append({
            "feature": feat,
            "feature_type": "numerical",
            "test": ks["test"],
            "statistic": ks["statistic"],
            "p_value": ks["p_value"],
            "magnitude_measure": ks["statistic"]
        })

    # 2. Categorical: Chi-square test
    cat_prof = baseline_profile.get("categorical_profile", {})
    for feat in CATEGORICAL_FEATURES:
        base_cats = sorted(cat_prof[feat]["frequencies"].keys())
        chi2 = run_chi_square_test(baseline_df[feat], batch_df[feat], baseline_categories=base_cats)
        tvd = compute_tvd(chi2["baseline_proportions"], chi2["batch_proportions"])
        results.append({
            "feature": feat,
            "feature_type": "categorical",
            "test": chi2["test"],
            "statistic": chi2["statistic"],
            "p_value": chi2["p_value"],
            "magnitude_measure": tvd
        })

    results_df = pd.DataFrame(results)

    # 3. Multiple testing correction: Benjamini-Hochberg FDR
    reject, adj_pvals, _, _ = multipletests(results_df["p_value"].values, alpha=alpha, method="fdr_bh")
    results_df["adjusted_p_value"] = adj_pvals
    results_df["drift_detected"] = (results_df["adjusted_p_value"] < alpha).astype(int)

    return results_df


# ── V9 Health Engine Methodology ─────────────────────────────────────

def calculate_data_health(drift_percentage: float) -> Tuple[float, str]:
    if drift_percentage == 0:
        return 100.0, "HEALTHY"
    elif drift_percentage <= 25:
        return 80.0, "LOW_DRIFT"
    elif drift_percentage <= 50:
        return 60.0, "MODERATE_DRIFT"
    elif drift_percentage <= 75:
        return 40.0, "HIGH_DRIFT"
    else:
        return 20.0, "VERY_HIGH_DRIFT"


def calculate_model_health(f1_degradation_pct: float) -> Tuple[float, str]:
    if f1_degradation_pct <= 0:
        return 100.0, "HEALTHY"
    elif f1_degradation_pct < 5:
        return 90.0, "STABLE"
    elif f1_degradation_pct < 10:
        return 75.0, "WATCH"
    elif f1_degradation_pct < 20:
        return 50.0, "DEGRADED"
    else:
        return 20.0, "SEVERELY_DEGRADED"


def apply_safety_overrides(initial_status: str, data_status: str, model_status: str) -> str:
    """Exact V9 safety override rules."""
    # Rule 2: Severely degraded model forces CRITICAL
    if model_status == "SEVERELY_DEGRADED":
        return "CRITICAL"

    # Rule 3: Very high drift with degraded model forces CRITICAL
    if data_status == "VERY_HIGH_DRIFT" and model_status == "DEGRADED":
        return "CRITICAL"

    # Rule 1: Degraded model overrides HEALTHY / MONITOR to INVESTIGATE
    if model_status == "DEGRADED" and initial_status in ["HEALTHY", "MONITOR"]:
        return "INVESTIGATE"

    # Rule 4: High or very high drift with stable/healthy model forces MONITOR
    if data_status in ["HIGH_DRIFT", "VERY_HIGH_DRIFT"] and model_status in ["STABLE", "HEALTHY"]:
        return "MONITOR"

    return initial_status


def generate_recommendation(status: str, is_unlabeled: bool = False) -> str:
    if is_unlabeled:
        if status == "HEALTHY":
            return "Input data is stable relative to baseline. Ground-truth labels unavailable for model evaluation."
        else:
            return "Input distribution drift detected. Continue monitoring. Ground-truth labels unavailable for model performance evaluation."

    if status == "HEALTHY":
        return "Model and input data are currently stable. Continue routine monitoring."
    elif status == "MONITOR":
        return "Significant input distribution change detected, but model performance has not degraded beyond the configured threshold. Continue monitoring and investigate the drifting features."
    elif status == "INVESTIGATE":
        return "Evidence of model performance degradation has been detected. Investigate feature drift, label distribution, data quality, and model behavior before considering retraining."
    elif status == "CRITICAL":
        return "Severe model-health degradation detected. Investigate the production data pipeline and model immediately. Consider model rollback or retraining after root-cause analysis."
    return "Unknown status."


# ── Full Monitoring Execution Pipeline ───────────────────────────────

def register_batch_file(file_name: str, file_bytes: bytes, row_count: int,
                        col_count: int, schema_hash: str, has_target: bool) -> str:
    """
    Registers a new batch in SQLite and persists the original CSV artifact.
    Status lifecycle starts at UPLOADED.
    """
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    dest_path = INCOMING_DIR / f"{batch_id}.csv"

    # Persist physical CSV
    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incoming_batches (
            batch_id, file_name, uploaded_at, row_count, column_count,
            schema_hash, has_target, status, file_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        batch_id, file_name, now_str, row_count, col_count,
        schema_hash, int(has_target), "UPLOADED", str(dest_path)
    ))
    conn.commit()
    conn.close()

    return batch_id


def process_monitoring_batch(batch_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Executes the end-to-end monitoring pipeline for an existing registered batch:
    VALIDATING -> PROCESSING -> (Drift + Frozen XGBoost + Performance if labeled + V9 Health) -> COMPLETED.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Retrieve batch metadata
    cursor.execute("SELECT * FROM incoming_batches WHERE batch_id = ?", (batch_id,))
    batch_row = cursor.fetchone()
    if not batch_row:
        conn.close()
        return False, f"Batch '{batch_id}' not found in registry.", {}

    file_path = batch_row["file_path"]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update status: VALIDATING
    cursor.execute("""
        UPDATE incoming_batches 
        SET status = 'VALIDATING', processing_started_at = ?
        WHERE batch_id = ?
    """, (now_str, batch_id))
    conn.commit()

    try:
        # 1. File Validation
        is_file_valid, file_msg, raw_df = validate_file(file_path)
        if not is_file_valid:
            cursor.execute("UPDATE incoming_batches SET status = 'FAILED', error_message = ? WHERE batch_id = ?", (file_msg, batch_id))
            conn.commit()
            conn.close()
            return False, f"File validation failed: {file_msg}", {}

        # 2. Schema Validation
        baseline_profile = load_baseline_profile()
        schema_res = validate_schema(raw_df, baseline_profile)
        if not schema_res["is_valid"]:
            err_msg = "; ".join(schema_res["errors"])
            cursor.execute("UPDATE incoming_batches SET status = 'FAILED', error_message = ? WHERE batch_id = ?", (err_msg, batch_id))
            conn.commit()
            conn.close()
            return False, f"Schema validation failed: {err_msg}", {}

        # Update status: PROCESSING
        cursor.execute("UPDATE incoming_batches SET status = 'PROCESSING' WHERE batch_id = ?", (batch_id,))
        conn.commit()

        cleaned_df = schema_res["cleaned_df"]
        has_target = schema_res["has_target"]
        run_id = f"run_{uuid.uuid4().hex[:8]}"

        # 3. Create Monitoring Run
        cursor.execute("""
            INSERT INTO monitoring_runs (run_id, run_timestamp, baseline_version, source, batch_count)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, now_str, "v7", f"Batch {batch_id}", 1))

        # 4. Drift Detection (Reuse V7)
        baseline_df = get_baseline_dataset()
        drift_results = detect_drift(baseline_df, cleaned_df, baseline_profile)
        
        total_feats = len(drift_results)
        drifted_feats = int(drift_results["drift_detected"].sum())
        drift_pct = (drifted_feats / total_feats) * 100.0 if total_feats > 0 else 0.0

        if drift_pct < 20: severity = "LOW"
        elif drift_pct <= 50: severity = "MEDIUM"
        else: severity = "HIGH"

        # Insert batch drift summary
        cursor.execute("""
            INSERT INTO batch_drift_summary (run_id, batch_id, scenario, total_features, drifted_features, drift_percentage, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, batch_id, f"Upload: {batch_row['file_name']}", total_feats, drifted_feats, drift_pct, severity))

        # Insert feature-level drift
        feature_rows = []
        for _, row in drift_results.iterrows():
            feature_rows.append((
                run_id, batch_id, row["feature"], row["feature_type"], row["test"],
                row["statistic"], row["p_value"], row["adjusted_p_value"],
                row["magnitude_measure"], int(row["drift_detected"])
            ))
        cursor.executemany("""
            INSERT INTO feature_drift (run_id, batch_id, feature, feature_type, test_name, statistic, p_value, adjusted_p_value, magnitude, drift_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, feature_rows)

        # 5. Frozen XGBoost Predictions
        model = joblib.load(PROJECT_ROOT / "artifacts" / "models" / "churn_xgboost_v4_tuned.joblib")
        y_prob = model.predict_proba(cleaned_df[ALL_FEATURES])[:, 1]
        y_pred = (y_prob >= EXPECTED_THRESHOLD).astype(int)

        # 6. Performance Evaluation (V8)
        perf_summary = {}
        if has_target:
            y_true = cleaned_df[TARGET_COLUMN].map({"No": 0, "Yes": 1}).astype(int)
            acc = float(accuracy_score(y_true, y_pred))
            prec = float(precision_score(y_true, y_pred, zero_division=0))
            rec = float(recall_score(y_true, y_pred, zero_division=0))
            f1 = float(f1_score(y_true, y_pred, zero_division=0))
            auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0

            cm = confusion_matrix(y_true, y_pred)
            tn, fp, fn, tp = [int(v) for v in cm.ravel()]

            cursor.execute("""
                INSERT INTO performance_results (
                    run_id, batch_id, scenario, accuracy, precision, recall, f1, roc_auc,
                    tp, tn, fp, fn, threshold, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, batch_id, f"Upload: {batch_row['file_name']}",
                acc, prec, rec, f1, auc, tp, tn, fp, fn, EXPECTED_THRESHOLD, now_str
            ))

            f1_degradation_pct = ((BASELINE_F1 - f1) / BASELINE_F1) * 100.0
            f1_pct_change = ((f1 - BASELINE_F1) / BASELINE_F1) * 100.0
            current_f1 = f1

            perf_summary = {
                "accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "roc_auc": auc,
                "tp": tp, "tn": tn, "fp": fp, "fn": fn, "f1_change": f1_pct_change
            }
        else:
            current_f1 = None
            f1_pct_change = None
            f1_degradation_pct = None

        # 7. Deterministic Health Engine (V9)
        data_health_score, data_health_status = calculate_data_health(drift_pct)

        if has_target:
            model_health_score, model_health_status = calculate_model_health(f1_degradation_pct)
            overall_health_score = round(0.40 * data_health_score + 0.60 * model_health_score, 1)
            
            if overall_health_score >= 90: initial_status = "HEALTHY"
            elif overall_health_score >= 75: initial_status = "MONITOR"
            elif overall_health_score >= 50: initial_status = "INVESTIGATE"
            else: initial_status = "CRITICAL"

            overall_status = apply_safety_overrides(initial_status, data_health_status, model_status=model_health_status)
            recommendation = generate_recommendation(overall_status, is_unlabeled=False)
        else:
            # Unlabeled dataset - honest degradation
            model_health_score = None
            model_health_status = "INSUFFICIENT_EVIDENCE"
            overall_health_score = round(data_health_score, 1)
            if data_health_status == "HEALTHY":
                overall_status = "HEALTHY"
            else:
                overall_status = "MONITOR"
            recommendation = generate_recommendation(overall_status, is_unlabeled=True)

        cursor.execute("""
            INSERT INTO health_assessments (
                run_id, batch_id, scenario, drift_percentage, data_health_score, data_health_status,
                baseline_f1, current_f1, f1_percentage_change, model_health_score, model_health_status,
                overall_health_score, overall_health_status, recommendation, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, batch_id, f"Upload: {batch_row['file_name']}", drift_pct, data_health_score, data_health_status,
            BASELINE_F1, current_f1, f1_pct_change, model_health_score, model_health_status,
            overall_health_score, overall_status, recommendation, now_str
        ))

        # 8. Mark Batch COMPLETED
        completed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE incoming_batches 
            SET status = 'COMPLETED', processing_completed_at = ?
            WHERE batch_id = ?
        """, (completed_at, batch_id))

        conn.commit()
        conn.close()

        results_payload = {
            "batch_id": batch_id,
            "run_id": run_id,
            "drift_percentage": drift_pct,
            "drifted_features": drifted_feats,
            "total_features": total_feats,
            "data_health_score": data_health_score,
            "data_health_status": data_health_status,
            "has_target": has_target,
            "performance": perf_summary,
            "model_health_score": model_health_score,
            "model_health_status": model_health_status,
            "overall_health_score": overall_health_score,
            "overall_health_status": overall_status,
            "recommendation": recommendation
        }

        return True, "Batch processed successfully.", results_payload

    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        cursor.execute("UPDATE incoming_batches SET status = 'FAILED', error_message = ? WHERE batch_id = ?", (str(e), batch_id))
        conn.commit()
        conn.close()
        return False, f"Processing failed: {str(e)}", {"traceback": tb_str}


def run_monitoring_from_file(file_name: str, file_bytes: bytes) -> Tuple[bool, str, Dict[str, Any]]:
    """Convenience helper combining registration and monitoring for Streamlit upload."""
    import io
    # 1. Physical file validation first
    is_valid, msg, df = validate_file(io.BytesIO(file_bytes))
    if not is_valid or df is None:
        return False, f"File validation failed: {msg}", {}

    has_target = TARGET_COLUMN in df.columns
    schema_hash = compute_schema_hash(df, ALL_FEATURES, has_target)
    
    batch_id = register_batch_file(
        file_name=file_name,
        file_bytes=file_bytes,
        row_count=len(df),
        col_count=df.shape[1],
        schema_hash=schema_hash,
        has_target=has_target
    )
    
    return process_monitoring_batch(batch_id)


def run_monitoring(csv_path: str) -> Tuple[bool, str]:
    """Backward-compatible entry point accepting a CSV filepath."""
    try:
        path = Path(csv_path)
        with open(path, "rb") as f:
            file_bytes = f.read()
        success, msg, _ = run_monitoring_from_file(path.name, file_bytes)
        return success, msg
    except Exception as e:
        return False, str(e)
