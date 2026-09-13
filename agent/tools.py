import sqlite3
import pandas as pd
from pathlib import Path
from langchain_core.tools import tool
from app.config import DB_PATH, MONITORING_DIR

from typing import Optional, List, Dict, Any

def _query_db(query: str, params: tuple = ()) -> list:
    """Safe read-only wrapper for SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        return [{"error": str(e)}]

@tool
def get_batch_info(batch_id: Optional[str] = None):
    """Returns metadata about a specific monitored batch or the latest batches."""
    query = """
        SELECT batch_id, file_name, uploaded_at, row_count, column_count,
               schema_hash, has_target, status, processing_completed_at, error_message
        FROM incoming_batches
    """
    params = ()
    if batch_id:
        query += " WHERE batch_id = ?"
        params = (batch_id,)
    query += " ORDER BY uploaded_at DESC LIMIT 5"
    return _query_db(query, params)

@tool
def get_latest_health(scenario: Optional[str] = None, batch_id: Optional[str] = None):
    """Returns the V9 health assessment for the given scenario or batch_id."""
    query = """
        SELECT batch_id, scenario, drift_percentage, data_health_score, data_health_status,
               baseline_f1, current_f1, f1_percentage_change, model_health_score, 
               model_health_status, overall_health_score, overall_health_status, recommendation
        FROM health_assessments
    """
    params = ()
    if batch_id:
        query += " WHERE batch_id = ?"
        params = (batch_id,)
    elif scenario and scenario != "baseline":
        query += " WHERE scenario = ?"
        params = (scenario,)
    query += " ORDER BY created_at DESC LIMIT 3"
    return _query_db(query, params)

@tool
def get_drift_results(scenario: Optional[str] = None, batch_id: Optional[str] = None):
    """Returns V7.3 overall batch drift information for the given scenario or batch_id."""
    query = "SELECT * FROM batch_drift_summary"
    params = ()
    if batch_id:
        query += " WHERE batch_id = ?"
        params = (batch_id,)
    elif scenario and scenario != "baseline":
        query += " WHERE scenario = ?"
        params = (scenario,)
    query += " ORDER BY run_id DESC LIMIT 3"
    return _query_db(query, params)

@tool
def get_feature_drift(feature: Optional[str] = None, scenario: Optional[str] = None, batch_id: Optional[str] = None):
    """Returns drift information for all features or a specific feature for a batch."""
    query = "SELECT fd.* FROM feature_drift fd"
    params = []
    conditions = []
    
    if feature:
        conditions.append("fd.feature = ?")
        params.append(feature)
        
    if batch_id:
        conditions.append("fd.batch_id = ?")
        params.append(batch_id)
    elif scenario and scenario != "baseline":
        query += " JOIN batch_drift_summary bds ON fd.run_id = bds.run_id AND fd.batch_id = bds.batch_id"
        conditions.append("bds.scenario = ?")
        params.append(scenario)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY fd.drift_detected DESC, fd.magnitude DESC LIMIT 25"
    return _query_db(query, tuple(params))

@tool
def get_performance_results(scenario: Optional[str] = None, batch_id: Optional[str] = None):
    """Returns V8 performance metrics for a batch or scenario."""
    if batch_id or scenario == "User Upload":
        query = "SELECT * FROM performance_results"
        params = ()
        if batch_id:
            query += " WHERE batch_id = ?"
            params = (batch_id,)
        else:
            query += " ORDER BY evaluated_at DESC LIMIT 1"
        res = _query_db(query, params)
        if res and "error" not in res[0]:
            return res
        return [{"message": "Performance metrics unavailable: ground-truth labels not provided in this batch or batch was unlabeled."}]

    try:
        df = pd.read_csv(MONITORING_DIR / "performance_results_v8.csv")
        if scenario:
            scen_map = {"baseline": "baseline", "stable": "A_stable", "mild_shift": "B_moderate_shift", "strong_shift": "C_strong_shift"}
            v8_scen = scen_map.get(scenario, scenario)
            df = df[df['scenario'] == v8_scen]
        return df.to_dict('records')
    except Exception as e:
        return [{"error": str(e)}]

@tool
def get_monitoring_summary(scenario: Optional[str] = None, batch_id: Optional[str] = None):
    """Returns a compact combined summary from V7-V9."""
    query = """
        SELECT h.batch_id, h.scenario, h.overall_health_status, h.data_health_status,
               h.model_health_status, b.drift_percentage, h.f1_percentage_change, h.recommendation
        FROM health_assessments h
        JOIN batch_drift_summary b ON h.run_id = b.run_id AND h.batch_id = b.batch_id
    """
    params = ()
    if batch_id:
        query += " WHERE h.batch_id = ?"
        params = (batch_id,)
    elif scenario and scenario != "baseline":
        query += " WHERE h.scenario = ?"
        params = (scenario,)
    query += " ORDER BY h.created_at DESC LIMIT 3"
    return _query_db(query, params)
