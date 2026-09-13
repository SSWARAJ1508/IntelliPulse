import sqlite3
import pandas as pd
import json
import streamlit as st
from pathlib import Path
from app.config import DB_PATH, MONITORING_DIR, EXPECTED_THRESHOLD, PROJECT_ROOT

_DB_INITIALIZED = False

def init_db_schema_if_needed(conn: sqlite3.Connection):
    """
    Defensively ensures all 7 monitoring tables exist without modifying existing data.
    Uses CREATE TABLE IF NOT EXISTS.
    """
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    try:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS monitoring_runs (
            run_id TEXT PRIMARY KEY,
            run_timestamp TEXT NOT NULL,
            baseline_version TEXT NOT NULL,
            source TEXT NOT NULL,
            batch_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS batch_drift_summary (
            run_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            scenario TEXT,
            total_features INTEGER NOT NULL,
            drifted_features INTEGER NOT NULL,
            drift_percentage REAL NOT NULL,
            severity TEXT NOT NULL,
            PRIMARY KEY (run_id, batch_id),
            FOREIGN KEY (run_id) REFERENCES monitoring_runs(run_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS feature_drift (
            run_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            feature TEXT NOT NULL,
            feature_type TEXT NOT NULL,
            test_name TEXT NOT NULL,
            statistic REAL,
            p_value REAL,
            adjusted_p_value REAL,
            magnitude REAL,
            drift_detected INTEGER NOT NULL,
            PRIMARY KEY (run_id, batch_id, feature),
            FOREIGN KEY (run_id) REFERENCES monitoring_runs(run_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS health_assessments (
            run_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            scenario TEXT,
            drift_percentage REAL,
            data_health_score REAL,
            data_health_status TEXT,
            baseline_f1 REAL,
            current_f1 REAL,
            f1_percentage_change REAL,
            model_health_score REAL,
            model_health_status TEXT,
            overall_health_score REAL,
            overall_health_status TEXT,
            recommendation TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (run_id, batch_id),
            FOREIGN KEY (run_id) REFERENCES monitoring_runs(run_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS incoming_batches (
            batch_id TEXT PRIMARY KEY,
            model_id TEXT,
            file_name TEXT,
            uploaded_at TEXT,
            row_count INTEGER,
            column_count INTEGER,
            schema_hash TEXT,
            has_target INTEGER,
            status TEXT,
            error_message TEXT,
            processing_started_at TEXT,
            processing_completed_at TEXT,
            file_path TEXT
        );

        CREATE TABLE IF NOT EXISTS incoming_batch_rows (
            batch_id TEXT,
            row_number INTEGER,
            row_data TEXT,
            FOREIGN KEY (batch_id) REFERENCES incoming_batches(batch_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS performance_results (
            run_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            scenario TEXT,
            accuracy REAL,
            precision REAL,
            recall REAL,
            f1 REAL,
            roc_auc REAL,
            tp INTEGER,
            tn INTEGER,
            fp INTEGER,
            fn INTEGER,
            threshold REAL,
            evaluated_at TEXT NOT NULL,
            PRIMARY KEY (run_id, batch_id),
            FOREIGN KEY (run_id) REFERENCES monitoring_runs(run_id) ON DELETE CASCADE
        );
        """)
        conn.commit()
        _DB_INITIALIZED = True
    except Exception:
        pass

def get_db_connection():
    """Returns a SQLite connection with guaranteed schema initialization."""
    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db_schema_if_needed(conn)
    return conn

@st.cache_data(ttl=2)
def get_available_batches():
    """Retrieve all monitored batches from SQLite."""
    try:
        conn = get_db_connection()
        query = """
            SELECT batch_id, file_name, uploaded_at, row_count, column_count,
                   has_target, status, error_message, processing_completed_at
            FROM incoming_batches 
            ORDER BY uploaded_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=2)
def get_batch_metadata(batch_id):
    """Retrieve metadata for a specific batch."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM incoming_batches WHERE batch_id = ?", (batch_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None

@st.cache_data(ttl=2)
def load_health_assessments(scenario=None, batch_id=None):
    try:
        conn = get_db_connection()
        query = "SELECT * FROM health_assessments"
        params = []
        if batch_id:
            query += " WHERE batch_id = ?"
            params.append(batch_id)
        elif scenario and scenario != "baseline":
            query += " WHERE scenario = ?"
            params.append(scenario)
        query += " ORDER BY created_at DESC"
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=2)
def load_drift_summary(scenario=None, batch_id=None):
    try:
        conn = get_db_connection()
        query = "SELECT * FROM batch_drift_summary"
        params = []
        if batch_id:
            query += " WHERE batch_id = ?"
            params.append(batch_id)
        elif scenario and scenario != "baseline":
            query += " WHERE scenario = ?"
            params.append(scenario)
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=2)
def load_feature_drift(scenario=None, batch_id=None):
    try:
        conn = get_db_connection()
        if batch_id:
            query = """
                SELECT feature, feature_type, test_name, statistic, p_value, 
                       adjusted_p_value, magnitude, drift_detected 
                FROM feature_drift
                WHERE batch_id = ?
            """
            params = [batch_id]
        else:
            query = """
                SELECT fd.feature, fd.feature_type, fd.test_name, fd.statistic, fd.p_value, 
                       fd.adjusted_p_value, fd.magnitude, fd.drift_detected 
                FROM feature_drift fd
                JOIN batch_drift_summary bds ON fd.run_id = bds.run_id AND fd.batch_id = bds.batch_id
            """
            params = []
            if scenario and scenario != "baseline":
                query += " WHERE bds.scenario = ?"
                params.append(scenario)

        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def validate_threshold():
    try:
        with open(MONITORING_DIR / "performance_baseline_v8.json", "r") as f:
            v8_base = json.load(f)
            actual_threshold = v8_base.get("threshold")
            if actual_threshold != EXPECTED_THRESHOLD:
                return False, actual_threshold
            return True, actual_threshold
    except Exception:
        return False, None

def map_scenario_to_v8(scenario):
    """Map standard scenario strings to V8 specific names."""
    if scenario == "baseline": return "baseline"
    if scenario == "stable": return "A_stable"
    if scenario == "mild_shift": return "B_moderate_shift"
    if scenario == "strong_shift": return "C_strong_shift"
    return scenario

@st.cache_data(ttl=2)
def get_performance_results(scenario=None, batch_id=None):
    """Retrieve performance results from SQLite for uploaded batches, or CSV for V8 baseline."""
    try:
        conn = get_db_connection()
        if batch_id:
            query = "SELECT * FROM performance_results WHERE batch_id = ?"
            df = pd.read_sql(query, conn, params=[batch_id])
            conn.close()
            return df

        if scenario == "User Upload":
            query = "SELECT * FROM performance_results ORDER BY evaluated_at DESC LIMIT 1"
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        conn.close()
    except Exception:
        pass

    try:
        df = pd.read_csv(MONITORING_DIR / "performance_results_v8.csv")
        if scenario:
            v8_scen = map_scenario_to_v8(scenario)
            df = df[df['scenario'] == v8_scen]
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=2)
def get_confusion_matrix(scenario=None, batch_id=None):
    """Retrieve confusion matrix."""
    if batch_id or scenario == "User Upload":
        conn = get_db_connection()
        c = conn.cursor()
        if batch_id:
            c.execute("SELECT tp, tn, fp, fn FROM performance_results WHERE batch_id = ?", (batch_id,))
        else:
            c.execute("SELECT tp, tn, fp, fn FROM performance_results ORDER BY evaluated_at DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row and row["tp"] is not None:
            tp, tn, fp, fn = int(row["tp"]), int(row["tn"]), int(row["fp"]), int(row["fn"])
            cm = [[tn, fp], [fn, tp]]
            return {
                "confusion_matrix": cm,
                "matrix": cm,
                "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                "labels": ["No Churn (0)", "Churn (1)"],
                "format": "[[TN, FP], [FN, TP]]"
            }
        return {}

    try:
        with open(MONITORING_DIR / "confusion_matrices_v8.json", "r") as f:
            data = json.load(f)
            if scenario:
                v8_scen = map_scenario_to_v8(scenario)
                scen_dict = data.get("matrices", {}).get(v8_scen, {})
                cm = scen_dict.get("confusion_matrix", [])
                if cm and len(cm) == 2:
                    tn, fp = int(cm[0][0]), int(cm[0][1])
                    fn, tp = int(cm[1][0]), int(cm[1][1])
                    return {
                        "confusion_matrix": [[tn, fp], [fn, tp]],
                        "matrix": [[tn, fp], [fn, tp]],
                        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                        "labels": scen_dict.get("labels", ["No Churn (0)", "Churn (1)"]),
                        "format": scen_dict.get("format", "[[TN, FP], [FN, TP]]")
                    }
                return scen_dict
            return data
    except Exception:
        return {}

@st.cache_data(ttl=2)
def get_recent_monitoring_events():
    """Retrieve a mixed feed of recent monitoring events."""
    conn = get_db_connection()
    events = []
    
    # 1. Incoming batch events
    try:
        batch_query = "SELECT batch_id, file_name, status, uploaded_at FROM incoming_batches ORDER BY uploaded_at DESC LIMIT 3"
        for row in conn.execute(batch_query).fetchall():
            status = row['status']
            color = "var(--success)" if status == "COMPLETED" else "var(--danger)" if status == "FAILED" else "var(--warning)"
            events.append({
                "type": "Batch Registry",
                "title": f"Batch {row['status']}: {row['file_name']}",
                "desc": f"ID: {row['batch_id']}",
                "time": row['uploaded_at'],
                "color": color
            })
    except Exception:
        pass

    # 2. Health events
    try:
        health_query = "SELECT created_at, overall_health_status, scenario, batch_id FROM health_assessments ORDER BY created_at DESC LIMIT 3"
        for row in conn.execute(health_query).fetchall():
            status = row['overall_health_status']
            color = "var(--success)" if status == "HEALTHY" else "var(--warning)" if status in ["MONITOR", "INVESTIGATE"] else "var(--danger)"
            events.append({
                "type": "Health Assessment",
                "title": f"Health check: {status}",
                "desc": f"Batch: {row['batch_id']} ({row['scenario']})",
                "time": row['created_at'],
                "color": color
            })
    except Exception:
        pass
        
    conn.close()
    return events
