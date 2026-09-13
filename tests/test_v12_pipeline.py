import os
import sys
import io
import json
import sqlite3
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.config import DB_PATH, MONITORING_DIR, EXPECTED_THRESHOLD
from app.services.validation import validate_file, validate_schema, compute_data_quality_summary, ALL_FEATURES
from app.services.monitoring_pipeline import run_monitoring_from_file, load_baseline_profile, process_monitoring_batch
from app.data_access import get_available_batches, load_health_assessments, get_performance_results


def run_v12_tests():
    print("=" * 80)
    print("  INTELLIPULSE V12 — PRODUCTION OBSERVABILITY TEST MATRIX")
    print("=" * 80)
    
    validation_log = []
    
    def check(test_num, name, condition, details=""):
        status = "PASS" if condition else "FAIL"
        validation_log.append((test_num, name, status, details))
        icon = "✓" if condition else "✗"
        print(f"  [{status}] {icon} Test {test_num}: {name}")
        if details and not condition:
            print(f"         Detail: {details}")

    # Baseline Profile
    base_prof = load_baseline_profile()
    raw_df = pd.read_csv(PROJECT_ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv")

    # ─────────────────────────────────────────────────────────────────
    # 1. Stable Labeled CSV
    # ─────────────────────────────────────────────────────────────────
    stable_labeled_df = raw_df.head(500).copy()
    stable_labeled_bytes = stable_labeled_df.to_csv(index=False).encode('utf-8')
    s1, msg1, res1 = run_monitoring_from_file("stable_labeled_sample.csv", stable_labeled_bytes)
    
    check(1, "Stable Labeled CSV Processing", s1, msg1)
    if s1:
        check(1.1, "Stable Labeled has_target == True", res1.get("has_target") is True)
        check(1.2, "Stable Labeled Artifact Persisted", (MONITORING_DIR / "incoming_batches" / f"{res1['batch_id']}.csv").exists())
        check(1.3, "Stable Labeled Performance Saved", res1.get("performance", {}).get("f1") is not None)
        check(1.4, "Stable Labeled Health Computed", res1.get("overall_health_score") is not None)

    # ─────────────────────────────────────────────────────────────────
    # 2. Stable Unlabeled CSV
    # ─────────────────────────────────────────────────────────────────
    stable_unlabeled_df = raw_df.head(500).drop(columns=["Churn"]).copy()
    stable_unlabeled_bytes = stable_unlabeled_df.to_csv(index=False).encode('utf-8')
    s2, msg2, res2 = run_monitoring_from_file("stable_unlabeled_sample.csv", stable_unlabeled_bytes)
    
    check(2, "Stable Unlabeled CSV Processing", s2, msg2)
    if s2:
        check(2.1, "Stable Unlabeled has_target == False", res2.get("has_target") is False)
        check(2.2, "Stable Unlabeled Performance Omitted Honestly", res2.get("performance") == {})
        check(2.3, "Stable Unlabeled Model Health INSUFFICIENT_EVIDENCE", res2.get("model_health_status") == "INSUFFICIENT_EVIDENCE")

    # ─────────────────────────────────────────────────────────────────
    # 3. High Drift Labeled CSV
    # ─────────────────────────────────────────────────────────────────
    high_drift_path = PROJECT_ROOT / "intellipulse_high_drift_churn.csv"
    with open(high_drift_path, "rb") as f:
        hd_labeled_bytes = f.read()
    s3, msg3, res3 = run_monitoring_from_file("intellipulse_high_drift_churn.csv", hd_labeled_bytes)
    
    check(3, "High Drift Labeled CSV Processing", s3, msg3)
    if s3:
        check(3.1, "High Drift Detected (>20% drift)", res3.get("drift_percentage", 0) > 20.0, f"Drift: {res3.get('drift_percentage')}%")
        check(3.2, "High Drift Labeled Performance Evaluated", res3.get("performance", {}).get("f1") is not None)
        check(3.3, "High Drift Safety Override Applied", res3.get("overall_health_status") in ["MONITOR", "INVESTIGATE", "CRITICAL"])

    # ─────────────────────────────────────────────────────────────────
    # 4. High Drift Unlabeled CSV
    # ─────────────────────────────────────────────────────────────────
    high_drift_unlabeled_path = PROJECT_ROOT / "intellipulse_high_drift_churn_unlabeled.csv"
    with open(high_drift_unlabeled_path, "rb") as f:
        hd_unlabeled_bytes = f.read()
    s4, msg4, res4 = run_monitoring_from_file("intellipulse_high_drift_churn_unlabeled.csv", hd_unlabeled_bytes)
    
    check(4, "High Drift Unlabeled CSV Processing", s4, msg4)
    if s4:
        check(4.1, "High Drift Unlabeled has_target == False", res4.get("has_target") is False)
        check(4.2, "High Drift Unlabeled skips performance honestly", res4.get("performance") == {})
        check(4.3, "High Drift Unlabeled reports MONITOR / Data Drift", res4.get("overall_health_status") == "MONITOR")

    # ─────────────────────────────────────────────────────────────────
    # 5. Missing Columns
    # ─────────────────────────────────────────────────────────────────
    df_missing = raw_df[["tenure", "MonthlyCharges"]].head(10)
    missing_bytes = df_missing.to_csv(index=False).encode('utf-8')
    s5, msg5, _ = run_monitoring_from_file("missing_cols.csv", missing_bytes)
    check(5, "Missing Columns Validation Failure (Stopped)", not s5 and "Missing required feature columns" in msg5)

    # ─────────────────────────────────────────────────────────────────
    # 6. Invalid Category
    # ─────────────────────────────────────────────────────────────────
    df_inv_cat = raw_df.head(20).copy()
    df_inv_cat.loc[0, "Contract"] = "Super Contract VIP"
    inv_cat_bytes = df_inv_cat.to_csv(index=False).encode('utf-8')
    s6, msg6, _ = run_monitoring_from_file("invalid_category.csv", inv_cat_bytes)
    check(6, "Invalid Category Rejection (Stopped)", not s6 and "unrecognized categories" in msg6)

    # ─────────────────────────────────────────────────────────────────
    # 7. Invalid Numeric Values
    # ─────────────────────────────────────────────────────────────────
    df_inv_num = raw_df.head(20).copy()
    df_inv_num.loc[0, "tenure"] = -99
    inv_num_bytes = df_inv_num.to_csv(index=False).encode('utf-8')
    s7, msg7, _ = run_monitoring_from_file("invalid_numerics.csv", inv_num_bytes)
    check(7, "Invalid Numeric Values Rejection (Stopped)", not s7 and "negative values" in msg7)

    # ─────────────────────────────────────────────────────────────────
    # 8. Empty CSV
    # ─────────────────────────────────────────────────────────────────
    empty_bytes = b""
    s8, msg8, _ = run_monitoring_from_file("empty.csv", empty_bytes)
    check(8, "Empty CSV Rejection (Stopped)", not s8 and ("empty" in msg8.lower() or "no data" in msg8.lower()))

    # ─────────────────────────────────────────────────────────────────
    # 9. Duplicate Upload (Independent Batches)
    # ─────────────────────────────────────────────────────────────────
    dup_bytes = raw_df.head(100).to_csv(index=False).encode('utf-8')
    s9_1, _, res9_1 = run_monitoring_from_file("duplicate_run1.csv", dup_bytes)
    s9_2, _, res9_2 = run_monitoring_from_file("duplicate_run2.csv", dup_bytes)
    check(9, "Duplicate Uploads Create Unique Batches", (
        s9_1 and s9_2 and res9_1["batch_id"] != res9_2["batch_id"]
    ))

    # ─────────────────────────────────────────────────────────────────
    # 10. Streamlit Rerun Safety & SQLite Persistence Check
    # ─────────────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check incoming_batches has metadata
    c.execute("SELECT count(*) FROM incoming_batches WHERE status = 'COMPLETED'")
    completed_batches = c.fetchone()[0]
    
    # Check performance_results table
    c.execute("SELECT count(*) FROM performance_results")
    perf_count = c.fetchone()[0]
    
    # Check batch_drift_summary
    c.execute("SELECT count(*) FROM batch_drift_summary")
    drift_count = c.fetchone()[0]
    
    # Check health_assessments
    c.execute("SELECT count(*) FROM health_assessments")
    health_count = c.fetchone()[0]
    
    conn.close()
    
    check(10, "Persistence across all SQLite tables verified", (
        completed_batches >= 4 and perf_count >= 2 and drift_count >= 4 and health_count >= 4
    ), f"Batches: {completed_batches}, Perf: {perf_count}, Drift: {drift_count}, Health: {health_count}")

    # Overall summary
    print("=" * 80)
    passed_count = sum(1 for item in validation_log if item[2] == "PASS")
    total_count = len(validation_log)
    print(f"  TEST RESULTS: {passed_count}/{total_count} PASSED ({passed_count/total_count*100:.1f}%)")
    print("=" * 80)
    return passed_count == total_count


if __name__ == "__main__":
    success = run_v12_tests()
    sys.exit(0 if success else 1)
