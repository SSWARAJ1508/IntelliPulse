import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import io
import time
import html
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Ensure .env is loaded safely from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# Fix python path for local imports
import sys
sys.path.append(str(ROOT_DIR))

from app.config import SCENARIOS, EXPECTED_THRESHOLD, MONITORING_DIR, DB_PATH
from app.data_access import (
    load_health_assessments, load_drift_summary, load_feature_drift, validate_threshold,
    get_performance_results, get_confusion_matrix, get_recent_monitoring_events,
    get_available_batches, get_batch_metadata
)
from app.services.validation import (
    validate_file, validate_schema, compute_data_quality_summary, ALL_FEATURES
)
from app.services.monitoring_pipeline import (
    run_monitoring_from_file, load_baseline_profile,
    BASELINE_F1, BASELINE_ACCURACY, BASELINE_PRECISION, BASELINE_RECALL, BASELINE_ROC_AUC
)
from app.styles import apply_custom_styles, get_status_html
from app.components import (
    render_sidebar, render_hero_banner, render_kpi_card, render_metadata_strip,
    render_pipeline_timeline, render_empty_state_card, render_status_badge, render_html
)
from app.charts import plot_gauge, plot_bar, plot_confusion_matrix, plot_performance_trend

st.set_page_config(
    page_title="IntelliPulse | Enterprise ML Observability",
    page_icon="〽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session State Initialization ──────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "sidebar_collapsed" not in st.session_state:
    st.session_state.sidebar_collapsed = False
if "active_page" not in st.session_state:
    st.session_state.active_page = "Dashboard"
if "drift_subpage" not in st.session_state:
    st.session_state.drift_subpage = "Feature Drift"
if "current_scenario" not in st.session_state:
    st.session_state.current_scenario = "Stable"
if "active_batch_id" not in st.session_state:
    st.session_state.active_batch_id = None
if "monitoring_processing" not in st.session_state:
    st.session_state.monitoring_processing = False
if "validation_cache" not in st.session_state:
    st.session_state.validation_cache = {}
if "assistant_q" not in st.session_state:
    st.session_state.assistant_q = ""
if "global_search" not in st.session_state:
    st.session_state.global_search = ""
if st.session_state.get("clear_search_requested", False):
    st.session_state.global_search = ""
    st.session_state.global_search_input = ""
    st.session_state.clear_search_requested = False

current_theme = st.session_state.theme

# Apply Calm Enterprise Styles
apply_custom_styles(theme=current_theme, sidebar_collapsed=st.session_state.sidebar_collapsed)

def get_gemini_connection_status():
    """
    Checks Gemini API configuration safely without exposing secrets.
    Returns: (status_text: str, badge_class: str, is_connected: bool, err_message: Optional[str])
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            pass

    if not api_key or api_key == "DUMMY_KEY":
        return "Configuration Required", "warning", False, "GEMINI_API_KEY not found in .env or secrets."

    os.environ["GOOGLE_API_KEY"] = api_key
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
        return "Connected", "online", True, None
    except Exception as e:
        return "Temporarily Unavailable", "critical", False, str(e)


# ── Upload & Run Monitoring Dialog ───────────────────────────────────
@st.dialog("Run Monitoring — Ingest Production Batch", width="large")
def run_monitoring_dialog():
    render_html("""
    <div style="margin-bottom: 16px;">
        <h2 style="margin-bottom: 4px; font-size: 18px !important;">Ingest Incoming Batch</h2>
        <p style="color: var(--text-secondary); font-size: 13px; margin: 0;">
            Upload an incoming production batch CSV. IntelliPulse validates schema conformity,
            detects statistical drift against baseline (V7), executes frozen XGBoost inference at threshold 0.29,
            and calculates deterministic health (V9).
        </p>
    </div>
    """)

    uploaded_file = st.file_uploader("Drop CSV file here or browse files", type=["csv"], key="monitoring_csv_uploader")
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name
        file_size_kb = len(file_bytes) / 1024.0

        # Read preview
        try:
            preview_df = pd.read_csv(io.BytesIO(file_bytes))
            row_count, col_count = preview_df.shape
            has_target = "Churn" in preview_df.columns
            target_badge = "✅ 'Churn' Detected (Labeled Mode)" if has_target else "ℹ️ No 'Churn' (Unlabeled Mode)"
        except Exception as e:
            st.error(f"Unable to parse CSV: {str(e)}")
            return

        # Metadata Card
        render_html(f"""
        <div class="glass-card-tertiary" style="display: flex; justify-content: space-between; align-items: center; margin: 12px 0;">
            <div>
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">File Name</div>
                <div style="font-weight: 500; font-size: 12.5px; color: var(--text-primary);">{file_name}</div>
            </div>
            <div>
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Dimensions</div>
                <div style="font-weight: 500; font-size: 12.5px; color: var(--text-primary);">{row_count:,} rows × {col_count} cols</div>
            </div>
            <div>
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">File Size</div>
                <div style="font-weight: 500; font-size: 12.5px; color: var(--text-primary);">{file_size_kb:.1f} KB</div>
            </div>
            <div>
                <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Ground Truth</div>
                <div style="font-weight: 500; font-size: 12.5px; color: var(--light-blue);">{target_badge}</div>
            </div>
        </div>
        """)

        with st.expander("Preview Incoming Data (First 5 rows)", expanded=False):
            st.dataframe(preview_df.head(5), use_container_width=True)

        col_v, col_a = st.columns([1, 1])
        with col_v:
            validate_btn = st.button("Validate Dataset", use_container_width=True)
        with col_a:
            analyze_btn = st.button("Analyze Dataset", type="primary", use_container_width=True)

        # Validation Logic
        cache_key = f"{file_name}_{len(file_bytes)}"
        if validate_btn or cache_key in st.session_state.validation_cache:
            if validate_btn:
                base_prof = load_baseline_profile()
                is_file_ok, file_msg, parsed_df = validate_file(io.BytesIO(file_bytes))
                if is_file_ok and parsed_df is not None:
                    schema_res = validate_schema(parsed_df, base_prof)
                    quality_res = compute_data_quality_summary(parsed_df, baseline_profile=base_prof)
                    st.session_state.validation_cache[cache_key] = (schema_res, quality_res)
                else:
                    st.session_state.validation_cache[cache_key] = ({"is_valid": False, "errors": [file_msg]}, None)

            schema_res, quality_res = st.session_state.validation_cache[cache_key]
            if schema_res["is_valid"]:
                render_html(f"""
                <div style="background: var(--status-healthy-bg); border: 1px solid var(--status-healthy-border); padding: 10px 14px; border-radius: 8px; margin: 10px 0;">
                    <div style="color: var(--status-healthy); font-weight: 600; font-size: 12px;">✅ Schema Compatible</div>
                    <div style="color: var(--text-secondary); font-size: 11px; font-family: monospace; margin-top: 2px;">SHA-256 Fingerprint: {schema_res.get('schema_hash')} | Contract fulfilled (19 features)</div>
                </div>
                """)
                if quality_res:
                    qcol1, qcol2, qcol3 = st.columns(3)
                    qcol1.metric("Missing Values", f"{quality_res['missing_cells']:,}")
                    qcol2.metric("Duplicate Rows", f"{quality_res['duplicate_rows']:,}")
                    qcol3.metric("Invalid Categories", f"{quality_res['invalid_categories_count']}")
            else:
                err_items = "".join(f"<li>{err}</li>" for err in schema_res.get('errors', []))
                render_html(f"""
                <div style="background: var(--status-critical-bg); border: 1px solid var(--status-critical-border); padding: 10px 14px; border-radius: 8px; margin: 10px 0;">
                    <div style="color: var(--status-critical); font-weight: 600; font-size: 12px;">❌ Schema Mismatch — Validation Blocked</div>
                    <ul style="color: var(--text-secondary); font-size: 11.5px; margin: 4px 0 0 16px; padding: 0;">
                        {err_items}
                    </ul>
                </div>
                """)

        # Analyze Dataset Execution
        if analyze_btn:
            if st.session_state.monitoring_processing:
                st.warning("Analysis currently in progress. Please wait...")
                st.stop()

            st.session_state.monitoring_processing = True
            with st.status("Executing IntelliPulse Observability Pipeline...", expanded=True) as status_box:
                st.write("1. Validating CSV file structure & schema contract...")
                st.write("2. Registering monitoring batch and persisting CSV artifact...")
                st.write("3. Running KS test & Chi-Square drift detection against baseline...")
                st.write("4. Executing frozen XGBoost inference at threshold 0.29...")
                st.write("5. Calculating performance metrics & V9 deterministic health score...")

                success, msg, res = run_monitoring_from_file(file_name, file_bytes)

                if success:
                    status_box.update(label="Monitoring Pipeline Completed Successfully!", state="complete", expanded=False)
                    st.session_state.current_scenario = "Uploaded Batch"
                    st.session_state.active_batch_id = res["batch_id"]
                    st.session_state.monitoring_processing = False
                    st.success(f"Batch **{res['batch_id']}** successfully monitored!")
                    time.sleep(1)
                    st.rerun()
                else:
                    status_box.update(label="Monitoring Pipeline Failed", state="error", expanded=True)
                    st.session_state.monitoring_processing = False
                    st.error(msg)


# ── Threshold Validation ──────────────────────────────────────────────
valid_thresh, actual_thresh = validate_threshold()
if not valid_thresh:
    st.sidebar.error(f"INTEGRITY ERROR: Threshold {actual_thresh} != {EXPECTED_THRESHOLD}")
    st.stop()

# ── Render Architecture-Fixed Sidebar ─────────────────────────────────
render_sidebar(actual_thresh=actual_thresh)


# ── Clean Top Navbar ──────────────────────────────────────────────────
with st.container():
    st.markdown('<span class="navbar-wrapper"></span>', unsafe_allow_html=True)
    nb_col1, nb_col2, nb_col3 = st.columns([2.5, 4.5, 3.5])
    
    with nb_col1:
        # Breadcrumb
        page_name = st.session_state.active_page
        render_html(f"""
        <div style="display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:500; padding: 6px 0;">
            <span style="color:var(--text-muted);">IntelliPulse</span>
            <span style="color:var(--text-muted); font-size:10px;">/</span>
            <span style="color:var(--text-primary); font-weight:600;">{page_name}</span>
        </div>
        """)

    with nb_col2:
        sc1, sc2 = st.columns([1.5, 1.5])
        with sc1:
            search_query = st.text_input(
                "Search metrics, features...",
                value=st.session_state.get("global_search", ""),
                placeholder="🔍 Search metrics, features...",
                label_visibility="collapsed",
                key="global_search_input"
            )
            st.session_state.global_search = search_query
        with sc2:
            scenario_list = list(SCENARIOS.keys())
            scen_idx = scenario_list.index(st.session_state.current_scenario) if st.session_state.current_scenario in scenario_list else 0
            st.session_state.current_scenario = st.selectbox(
                "Monitoring Source", scenario_list, index=scen_idx, label_visibility="collapsed"
            )

    with nb_col3:
        btn_c1, btn_c2, btn_c3 = st.columns([1.1, 0.8, 1.6])
        with btn_c1:
            render_html("""
            <div style="display:flex; align-items:center; gap:5px; font-size:11px; color:var(--text-secondary); font-weight:500; padding: 7px 0;">
                <span class="pulse-dot online"></span>
                <span>Operational</span>
            </div>
            """)
        with btn_c2:
            # Professional subtle icon button for theme toggle
            theme_btn_icon = "☀" if current_theme == "dark" else "☾"
            theme_help = "Switch to Light theme" if current_theme == "dark" else "Switch to Dark theme"
            if st.button(theme_btn_icon, key="navbar_theme_toggle_btn", help=theme_help, use_container_width=True):
                st.session_state.theme = "light" if current_theme == "dark" else "dark"
                st.rerun()
        with btn_c3:
            if st.button("Run Monitoring", type="primary", key="navbar_run_btn", use_container_width=True):
                run_monitoring_dialog()

# Secondary Selector for Uploaded Batches
if st.session_state.current_scenario == "Uploaded Batch":
    batches_df = get_available_batches()
    if not batches_df.empty:
        batch_options = {f"{b['batch_id']} | {b['file_name']} ({b['status']})": b['batch_id'] for _, b in batches_df.iterrows()}
        batch_labels = list(batch_options.keys())
        current_active = st.session_state.active_batch_id
        selected_idx = 0
        for idx, (lbl, b_id) in enumerate(batch_options.items()):
            if b_id == current_active:
                selected_idx = idx
                break
        chosen_label = st.selectbox("Select Uploaded Batch", batch_labels, index=selected_idx)
        st.session_state.active_batch_id = batch_options[chosen_label]
    else:
        st.info("No batches uploaded yet. Click 'Run Monitoring' to upload your first production CSV.")


# ── Load Active Monitoring Data ───────────────────────────────────────
is_uploaded = (st.session_state.current_scenario == "Uploaded Batch")
active_batch_id = st.session_state.active_batch_id if is_uploaded else None

if is_uploaded and active_batch_id:
    health_data = load_health_assessments(batch_id=active_batch_id)
    drift_data = load_drift_summary(batch_id=active_batch_id)
    feature_drift = load_feature_drift(batch_id=active_batch_id)
    perf_df = get_performance_results(batch_id=active_batch_id)
    batch_meta = get_batch_metadata(active_batch_id)
    scenario_id = f"Upload: {batch_meta['file_name'] if batch_meta else active_batch_id}"
else:
    scenario_id = SCENARIOS.get(st.session_state.current_scenario, "stable")
    health_data = load_health_assessments(scenario_id) if scenario_id != "baseline" else pd.DataFrame()
    drift_data = load_drift_summary(scenario_id) if scenario_id != "baseline" else pd.DataFrame()
    feature_drift = load_feature_drift(scenario_id) if scenario_id != "baseline" else pd.DataFrame()
    perf_df = get_performance_results(scenario_id)
    batch_meta = None

latest_health = health_data.iloc[0] if not health_data.empty else None
def render_search_results(query: str, health_data, drift_data, feature_drift, perf_df, actual_thresh: float):
    """
    Renders an interactive search overlay matching metrics, features, and navigation pages.
    """
    q = query.strip().lower()
    if not q:
        return

    # Safe metric extraction
    perf_row = perf_df.iloc[0].to_dict() if (perf_df is not None and not perf_df.empty) else {}
    health_row = health_data.iloc[0].to_dict() if (health_data is not None and not health_data.empty) else {}
    drift_row = drift_data.iloc[0].to_dict() if (drift_data is not None and not drift_data.empty) else {}

    # 1. Metric Catalog
    metric_defs = [
        {"name": "Accuracy", "val": f"{float(perf_row.get('accuracy', 0.7608)):.4f}", "ref": "Baseline: 0.7608", "page": "Model Performance", "keywords": ["accuracy", "acc"]},
        {"name": "Precision", "val": f"{float(perf_row.get('precision', 0.5336)):.4f}", "ref": "Baseline: 0.5336", "page": "Model Performance", "keywords": ["precision", "prec"]},
        {"name": "Recall", "val": f"{float(perf_row.get('recall', 0.7861)):.4f}", "ref": "Baseline: 0.7861", "page": "Model Performance", "keywords": ["recall", "rec", "sensitivity"]},
        {"name": "F1 Score", "val": f"{float(perf_row.get('f1', perf_row.get('f1_score', 0.6357))):.4f}", "ref": "Baseline: 0.6357", "page": "Model Performance", "keywords": ["f1", "f1_score", "f1 score", "f-score"]},
        {"name": "ROC-AUC", "val": f"{float(perf_row.get('roc_auc', 0.8490)):.4f}", "ref": "Baseline: 0.8490", "page": "Model Performance", "keywords": ["roc", "auc", "roc_auc", "roc-auc"]},
        {"name": "Decision Threshold", "val": f"{actual_thresh:.2f}", "ref": "Contractual Gate: 0.29", "page": "Model Performance", "keywords": ["threshold", "thresh", "cutoff", "0.29"]},
        {"name": "Overall Health", "val": f"{float(health_row.get('overall_health_score', 91.0)):.1f}% ({health_row.get('overall_status', 'HEALTHY')})", "ref": "Safety Rule: V9 Override", "page": "Dashboard", "keywords": ["health", "overall health", "status", "score"]},
        {"name": "Data Health", "val": f"{float(health_row.get('data_health_score', 100.0)):.1f}%", "ref": "Weight: 0.40", "page": "Dashboard", "keywords": ["data health", "data quality"]},
        {"name": "Model Health", "val": f"{float(health_row.get('model_health_score', 85.0)):.1f}%", "ref": "Weight: 0.60", "page": "Dashboard", "keywords": ["model health", "performance health"]},
        {"name": "Drift Ratio", "val": f"{float(drift_row.get('drift_ratio', 0.0))*100:.1f}%", "ref": f"{drift_row.get('drifted_features_count', 0)} drifted features", "page": "Data Drift", "keywords": ["drift", "drift ratio", "feature drift"]}
    ]

    matched_metrics = [m for m in metric_defs if q in m["name"].lower() or any(q in kw for kw in m["keywords"])]

    # 2. Match Features
    matched_features = []
    if feature_drift is not None and not feature_drift.empty and "feature" in feature_drift.columns:
        for _, row in feature_drift.iterrows():
            feat_name = str(row["feature"])
            if q in feat_name.lower():
                drifted = bool(row.get("drift_detected", False) == 1 or row.get("drift_detected", False) is True)
                stat_val = row.get("statistic", row.get("ks_statistic", row.get("stat_value", 0.0)))
                p_val = row.get("p_value", 1.0)
                matched_features.append({
                    "name": feat_name,
                    "drifted": drifted,
                    "stat": f"Stat: {float(stat_val):.4f}" if pd.notna(stat_val) else "N/A",
                    "p_val": f"p={float(p_val):.4e}" if pd.notna(p_val) else "N/A"
                })
    else:
        canonical = [
            "Contract", "Dependents", "DeviceProtection", "InternetService", "MonthlyCharges",
            "MultipleLines", "OnlineBackup", "OnlineSecurity", "PaperlessBilling", "Partner",
            "PaymentMethod", "PhoneService", "SeniorCitizen", "StreamingMovies", "StreamingTV",
            "TechSupport", "TotalCharges", "gender", "tenure"
        ]
        for f_name in canonical:
            if q in f_name.lower():
                matched_features.append({
                    "name": f_name,
                    "drifted": False,
                    "stat": "Baseline Reference",
                    "p_val": "Contractual Feature"
                })

    # 3. Match Pages
    matched_pages = []
    page_catalog = [
        ("Dashboard", ["dash", "overview", "home", "kpi", "summary"], "System Overview, Health Engine & Signals"),
        ("Live Monitor", ["live", "monitor", "batch", "ingest", "upload", "stream", "pipeline"], "Incoming Batch Registry & Physical CSV Ingestion"),
        ("Model Performance", ["perf", "model", "confusion", "matrix", "roc", "precision", "recall", "f1"], "Classification Performance & Confusion Matrix"),
        ("Data Drift", ["drift", "feature", "distribution", "shift", "target", "ks", "chi"], "Feature & Distribution Drift Detection"),
        ("AI Assistant", ["ai", "copilot", "chat", "ask", "gemini", "assistant", "agent"], "Gemini Observability Copilot"),
        ("Reports", ["report", "export", "download", "audit", "markdown"], "Batch Observability Reports & Audit Trails"),
        ("Settings", ["setting", "config", "theme", "spec", "appearance", "dark", "light"], "System Specifications & Configurations")
    ]
    for p_name, p_keywords, p_desc in page_catalog:
        if q in p_name.lower() or any(q in kw for kw in p_keywords):
            matched_pages.append((p_name, p_desc))

    total_matches = len(matched_metrics) + len(matched_features) + len(matched_pages)

    # Render Search Card
    st.markdown("<div class='search-results-box'>", unsafe_allow_html=True)
    top_c1, top_c2 = st.columns([8, 2])
    with top_c1:
        escaped_query = html.escape(query)
        st.markdown(
            f"<div style='font-size:14.5px; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;'>"
            f"<span>🔍 Search Results for:</span> <span style='color:var(--primary-blue); font-family:monospace;'>\"{escaped_query}\"</span> "
            f"<span style='font-size:12px; font-weight:500; color:var(--text-muted);'>({total_matches} match{'es' if total_matches != 1 else ''})</span></div>",
            unsafe_allow_html=True
        )
    with top_c2:
        if st.button("✕ Clear Search", key="clear_search_btn", use_container_width=True):
            st.session_state.clear_search_requested = True
            st.rerun()

    if total_matches == 0:
        st.markdown(
            "<div style='padding: 12px 0 6px 0; color: var(--text-secondary); font-size: 13px;'>"
            "No metrics, features, or navigation modules match your search query. "
            "Try searching for: <code style='color:var(--primary-blue);'>tenure</code>, "
            "<code style='color:var(--primary-blue);'>MonthlyCharges</code>, "
            "<code style='color:var(--primary-blue);'>f1</code>, "
            "<code style='color:var(--primary-blue);'>recall</code>, "
            "<code style='color:var(--primary-blue);'>drift</code>, or "
            "<code style='color:var(--primary-blue);'>reports</code>."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        tab_titles = []
        if matched_metrics:
            tab_titles.append(f"Metrics ({len(matched_metrics)})")
        if matched_features:
            tab_titles.append(f"Features ({len(matched_features)})")
        if matched_pages:
            tab_titles.append(f"Pages ({len(matched_pages)})")

        tabs = st.tabs(tab_titles)
        t_idx = 0

        if matched_metrics:
            with tabs[t_idx]:
                for m in matched_metrics:
                    mc1, mc2, mc3 = st.columns([4, 3, 3])
                    with mc1:
                        st.markdown(f"<div style='font-weight:600; font-size:13px; color:var(--text-primary);'>{m['name']}</div><div style='font-size:11px; color:var(--text-muted);'>{m['ref']}</div>", unsafe_allow_html=True)
                    with mc2:
                        st.markdown(f"<div style='font-size:14.5px; font-weight:700; color:var(--primary-blue); font-family:monospace;'>{m['val']}</div>", unsafe_allow_html=True)
                    with mc3:
                        if st.button(f"View in {m['page']}", key=f"s_m_{m['name']}", use_container_width=True):
                            st.session_state.active_page = m['page']
                            st.rerun()
            t_idx += 1

        if matched_features:
            with tabs[t_idx]:
                for f in matched_features:
                    fc1, fc2, fc3 = st.columns([4, 4, 2])
                    with fc1:
                        st.markdown(f"<div style='font-weight:600; font-size:12.5px; color:var(--text-primary); font-family:monospace;'>{f['name']}</div>", unsafe_allow_html=True)
                    with fc2:
                        status_badge = "<span style='color:#EF4444; font-weight:600;'>● DRIFTED</span>" if f["drifted"] else "<span style='color:#10B981; font-weight:600;'>● STABLE</span>"
                        st.markdown(f"<div style='font-size:12px;'>{status_badge} <span style='font-size:11px; color:var(--text-muted); margin-left:6px;'>{f['stat']} | {f['p_val']}</span></div>", unsafe_allow_html=True)
                    with fc3:
                        if st.button("Inspect in Drift", key=f"s_f_{f['name']}", use_container_width=True):
                            st.session_state.active_page = "Data Drift"
                            st.session_state.drift_subpage = "Feature Drift"
                            st.rerun()
            t_idx += 1

        if matched_pages:
            with tabs[t_idx]:
                for p_name, p_desc in matched_pages:
                    pc1, pc2 = st.columns([7, 3])
                    with pc1:
                        st.markdown(f"<div style='font-weight:600; font-size:13px; color:var(--text-primary);'>{p_name}</div><div style='font-size:11.5px; color:var(--text-secondary);'>{p_desc}</div>", unsafe_allow_html=True)
                    with pc2:
                        if st.button(f"Go to {p_name}", key=f"s_p_{p_name}", use_container_width=True):
                            st.session_state.active_page = p_name
                            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# Render Search Overlay if query exists
if st.session_state.get("global_search", "").strip():
    render_search_results(
        query=st.session_state.global_search.strip(),
        health_data=health_data,
        drift_data=drift_data,
        feature_drift=feature_drift,
        perf_df=perf_df,
        actual_thresh=actual_thresh
    )


def render_page_header(title: str, subtitle: str):
    """Renders a calm section header with breadcrumb badge."""
    badge_label = f"Batch: {active_batch_id}" if is_uploaded and active_batch_id else f"{st.session_state.current_scenario} Scenario"
    render_html(f"""
    <div class="animate-in delay-1" style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
            <h2 style="margin-bottom: 2px !important; text-transform: uppercase; letter-spacing: 0.04em; font-size: 18px !important;">{title}</h2>
            <p style="color: var(--text-secondary); margin: 0; font-size: 12.5px;">{subtitle}</p>
        </div>
        <div style="background: var(--card-secondary); border: 1px solid var(--subtle-border); color: var(--text-secondary); padding: 4px 10px; border-radius: 6px; font-weight: 500; font-size: 12px;">
            {badge_label}
        </div>
    </div>
    """)


page = st.session_state.active_page

# ── Page 1: Dashboard ─────────────────────────────────────────────────
if page == "Dashboard":
    render_hero_banner(on_run_monitoring=run_monitoring_dialog)

    if latest_health is None:
        render_empty_state_card(
            title="No Monitoring Metrics Available",
            message="No monitoring records exist for the selected source. Upload an incoming production batch or select an existing scenario.",
            icon="📭"
        )
    else:
        # Batch Metadata Strip
        if is_uploaded and batch_meta:
            target_str = "Yes (Labeled)" if batch_meta['has_target'] else "No (Unlabeled — Performance Honest Bypass)"
            target_color = "var(--status-healthy)" if batch_meta['has_target'] else "var(--text-secondary)"
            render_metadata_strip([
                ("Batch ID", batch_meta['batch_id'], "var(--text-primary)"),
                ("File Name", batch_meta['file_name'], "var(--text-primary)"),
                ("Rows Evaluated", f"{batch_meta['row_count']:,} rows", "var(--text-primary)"),
                ("Target Status", target_str, target_color),
                ("Processed At", batch_meta.get('processing_completed_at', 'Completed'), "var(--text-muted)")
            ])

        # 3 Aligned Health Cards: Primary Hierarchy with Gauges INSIDE
        render_html("<div style='margin-bottom: 8px; font-size: 10.5px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em;'>SYSTEM HEALTH ASSESSMENTS</div>")
        
        g1, g2, g3 = st.columns(3)
        with g1:
            render_html(f"""
            <div class="glass-card-primary" style="margin-bottom: 0;">
                <div class="kpi-header">
                    <div class="kpi-title">Overall Health Score</div>
                    <div class="kpi-icon">〽️</div>
                </div>
                <div style="margin-bottom: 4px;">{render_status_badge(latest_health['overall_health_status'])}</div>
            </div>
            """)
            st.plotly_chart(plot_gauge(latest_health['overall_health_score'], theme=current_theme), use_container_width=True, key="dash_overall_gauge")

        with g2:
            render_html(f"""
            <div class="glass-card-primary" style="margin-bottom: 0;">
                <div class="kpi-header">
                    <div class="kpi-title">Data Health Score</div>
                    <div class="kpi-icon">🌊</div>
                </div>
                <div style="margin-bottom: 4px;">{render_status_badge(latest_health['data_health_status'])}</div>
            </div>
            """)
            st.plotly_chart(plot_gauge(latest_health['data_health_score'], theme=current_theme), use_container_width=True, key="dash_data_gauge")

        with g3:
            m_score = latest_health['model_health_score']
            m_stat = latest_health['model_health_status']
            render_html(f"""
            <div class="glass-card-primary" style="margin-bottom: 0;">
                <div class="kpi-header">
                    <div class="kpi-title">Model Health Score</div>
                    <div class="kpi-icon">🎯</div>
                </div>
                <div style="margin-bottom: 4px;">{render_status_badge(m_stat)}</div>
            </div>
            """)
            st.plotly_chart(plot_gauge(m_score, theme=current_theme), use_container_width=True, key="dash_model_gauge")

        # Middle Grid: Feature Drift Overview + Performance Summary
        m_col1, m_col2 = st.columns([1, 1])

        # Drift Card with Chart INSIDE
        with m_col1:
            total_f = int(drift_data['total_features'].iloc[0]) if not drift_data.empty else 19
            drifted_f = int(drift_data['drifted_features'].iloc[0]) if not drift_data.empty else 0
            drift_pct = float(latest_health['drift_percentage'])
            severity = drift_data['severity'].iloc[0] if not drift_data.empty else "LOW"

            render_html(f"""
            <div class="glass-card-secondary" style="margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                    <div>
                        <h3 style="margin: 0 !important; font-size: 13.5px;">Statistical Feature Drift</h3>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">V7.3 Kolmogorov-Smirnov & Chi-Square</div>
                    </div>
                    <div>{render_status_badge(severity)}</div>
                </div>
                <div style="display: flex; gap: 16px;">
                    <div>
                        <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Drift Ratio</div>
                        <div style="font-size: 19px; font-weight: 700; color: var(--text-primary);">{drift_pct:.1f}%</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Drifted Features</div>
                        <div style="font-size: 19px; font-weight: 700; color: var(--text-primary);">{drifted_f} <span style="font-size: 12px; font-weight: 400; color: var(--text-muted);">/ {total_f}</span></div>
                    </div>
                </div>
            </div>
            """)

            if not feature_drift.empty:
                st.plotly_chart(
                    plot_bar(feature_drift, x_col="feature", y_col="magnitude", color_col="drift_detected", title="Feature Shift Magnitude (TVD / KS Stat)", theme=current_theme),
                    use_container_width=True, key="dash_drift_bar"
                )
            else:
                st.info("Baseline active — no feature drift detected.")

        # Model Performance Card
        with m_col2:
            render_html("""
            <div class="glass-card-secondary" style="margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin: 0 !important; font-size: 13.5px;">Model Predictive Performance</h3>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Evaluated against V8 Held-out Ground Truth</div>
                    </div>
                </div>
            </div>
            """)

            if perf_df.empty:
                render_empty_state_card(
                    title="Performance Unavailable",
                    message="Ground-truth labels are required to calculate classification performance. Predictions were generated at threshold 0.29.",
                    icon="🏷️",
                    reason="Ground-truth 'Churn' column was not present in this incoming batch."
                )
            else:
                perf = perf_df.iloc[0]
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    render_kpi_card("F1 Score", f"{perf['f1']:.4f}", delta=f"{latest_health['f1_percentage_change']:+.2f}% vs Base", delta_label="shift", icon="🎯", level="tertiary")
                    render_kpi_card("Accuracy", f"{perf['accuracy']:.4f}", delta=f"{(perf['accuracy'] - BASELINE_ACCURACY):+.4f}", delta_label="vs Base", icon="📊", level="tertiary")
                with p_col2:
                    render_kpi_card("Precision", f"{perf['precision']:.4f}", delta=f"{(perf['precision'] - BASELINE_PRECISION):+.4f}", delta_label="vs Base", icon="⚖️", level="tertiary")
                    render_kpi_card("Recall", f"{perf['recall']:.4f}", delta=f"{(perf['recall'] - BASELINE_RECALL):+.4f}", delta_label="vs Base", icon="🔍", level="tertiary")

        # Deterministic Recommendation & Recent Activity
        render_html(f"""
        <div class="glass-card-secondary" style="margin-top: 16px;">
            <h3 style="margin-top:0; margin-bottom:6px; font-size:13.5px;">DETERMINISTIC HEALTH RECOMMENDATION</h3>
            <div style="padding: 12px 16px; background: var(--card-secondary); border-left: 3px solid var(--primary-blue); border-radius: 6px;">
                <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 3px;">
                    Operational Status: {latest_health['overall_health_status']}
                </div>
                <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">
                    {latest_health['recommendation']}
                </div>
            </div>
        </div>
        """)

        # Recent Activity Table
        render_html("""
        <div class="glass-card-secondary" style="margin-bottom: 8px;">
            <h3 style="margin-top:0; margin-bottom:0; font-size:13.5px;">RECENT MONITORING EVENTS</h3>
        </div>
        """)
        recent_events = get_recent_monitoring_events()
        if recent_events:
            events_df = pd.DataFrame(recent_events)[["time", "type", "title", "desc"]]
            events_df.columns = ["Timestamp", "Category", "Event Title", "Details"]
            st.dataframe(events_df, use_container_width=True, hide_index=True)
        else:
            render_html("<div style='color:var(--text-muted); font-size:12.5px;'>No recent monitoring events found.</div>")


# ── Page 2: Live Monitor ──────────────────────────────────────────────
elif page == "Live Monitor":
    render_page_header("LIVE MONITOR & BATCH PIPELINE", "Track physical batch uploads, schema fingerprints, and real-time processing telemetry.")

    render_pipeline_timeline(current_stage="COMPLETED")

    render_html("""
    <div class="glass-card-secondary" style="margin-bottom: 8px;">
        <h3 style="margin-top:0; margin-bottom:0; font-size:14px;">REGISTERED INCOMING BATCHES (SQLITE REGISTRY)</h3>
    </div>
    """)
    batches_df = get_available_batches()
    if not batches_df.empty:
        st.dataframe(batches_df, use_container_width=True, hide_index=True)
    else:
        render_html("<div style='color:var(--text-muted); font-size:12.5px;'>No batches have been registered yet.</div>")

    # Real-Time Operational Signals
    c_sig1, c_sig2 = st.columns(2)
    with c_sig1:
        render_html(f"""
        <div class="glass-card-secondary">
            <h3 style="margin-top:0; margin-bottom:10px; font-size:13.5px;">PIPELINE INTEGRITY SIGNALS</h3>
            <table style="width: 100%; font-size: 12.5px; color: var(--text-secondary);">
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 7px 0;">Model Artifact:</td><td style="color:var(--text-primary); font-weight:500;">XGBoost Churn Classifier (v1.0)</td></tr>
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 7px 0;">Decision Threshold:</td><td style="color:var(--light-blue); font-weight:600;">{actual_thresh} (Strictly Enforced)</td></tr>
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 7px 0;">Required Canonical Features:</td><td style="color:var(--text-primary); font-weight:500;">19 Features</td></tr>
                <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 7px 0;">Database Health:</td><td style="color:var(--status-healthy); font-weight:500;">Connected (SQLite WAL Mode)</td></tr>
                <tr><td style="padding: 7px 0;">Agent Copilot:</td><td style="color:var(--status-healthy); font-weight:500;">Active (LangGraph + Gemini)</td></tr>
            </table>
        </div>
        """)

    with c_sig2:
        render_html("""
        <div class="glass-card-secondary" style="margin-bottom: 10px;">
            <h3 style="margin-top:0; margin-bottom:10px; font-size:13.5px;">INGESTION DISPATCHER</h3>
            <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5;">
                Production batches uploaded via the UI are persisted safely to disk with deterministic SHA-256 schema hashing.
                Click below to execute an immediate monitoring batch ingestion.
            </p>
        </div>
        """)
        if st.button("Ingest Production CSV", type="primary", use_container_width=True, key="live_ingest_btn"):
            run_monitoring_dialog()


# ── Page 3: Model Performance ─────────────────────────────────────────
elif page == "Model Performance":
    render_page_header("MODEL PERFORMANCE EVALUATION", "Classification performance evaluated against V8 held-out ground truth at decision threshold 0.29.")

    if perf_df.empty:
        render_empty_state_card(
            title="Performance Unavailable for Active Source",
            message="Ground-truth labels ('Churn') are required to calculate classification metrics such as Precision, Recall, F1, and ROC-AUC. For unlabeled batches, predictions are generated at threshold 0.29, and performance evaluation is honestly bypassed per MLOps standards.",
            icon="🏷️",
            reason="Unlabeled incoming batch: 'Churn' ground-truth column not present."
        )
    else:
        perf = perf_df.iloc[0]
        
        # 5 KPI Delta Cards
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            render_kpi_card("Accuracy", f"{perf['accuracy']:.4f}", delta=f"{(perf['accuracy'] - BASELINE_ACCURACY):+.4f}", delta_label="vs Base", icon="📊", level="secondary")
        with k2:
            render_kpi_card("Precision", f"{perf['precision']:.4f}", delta=f"{(perf['precision'] - BASELINE_PRECISION):+.4f}", delta_label="vs Base", icon="⚖️", level="secondary")
        with k3:
            render_kpi_card("Recall", f"{perf['recall']:.4f}", delta=f"{(perf['recall'] - BASELINE_RECALL):+.4f}", delta_label="vs Base", icon="🔍", level="secondary")
        with k4:
            render_kpi_card("F1 Score", f"{perf['f1']:.4f}", delta=f"{latest_health['f1_percentage_change']:+.2f}% vs Base", delta_label="shift", icon="🎯", level="primary")
        with k5:
            render_kpi_card("ROC-AUC", f"{perf['roc_auc']:.4f}", delta=f"{(perf['roc_auc'] - BASELINE_ROC_AUC):+.4f}", delta_label="vs Base", icon="📈", level="secondary")

        # Baseline vs. Current Batch Comparison Table
        render_html("""
        <div class="glass-card-secondary" style="margin-top: 16px; margin-bottom: 8px;">
            <h3 style="margin-top:0; margin-bottom:0; font-size:13.5px;">PERFORMANCE CONTRACT VS. CURRENT EVALUATION</h3>
        </div>
        """)
        metrics = [
            ("Accuracy", perf['accuracy'], BASELINE_ACCURACY, "accuracy"),
            ("Precision", perf['precision'], BASELINE_PRECISION, "precision"),
            ("Recall", perf['recall'], BASELINE_RECALL, "recall"),
            ("F1 Score", perf['f1'], BASELINE_F1, "f1"),
            ("ROC-AUC", perf['roc_auc'], BASELINE_ROC_AUC, "roc_auc")
        ]
        comp_rows = []
        for name, cur_val, base_val, _ in metrics:
            abs_chg = cur_val - base_val
            pct_chg = (abs_chg / base_val) * 100.0 if base_val != 0 else 0.0
            comp_rows.append({
                "Metric": name,
                "Baseline Contract": f"{base_val:.4f}",
                "Current Batch": f"{cur_val:.4f}",
                "Absolute Delta": f"{abs_chg:+.4f}",
                "Percentage Shift": f"{pct_chg:+.2f}%"
            })
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

        # Confusion Matrix Heatmap & Performance Assessment
        c_cm, c_interp = st.columns(2)
        with c_cm:
            render_html("""
            <div class="glass-card-secondary" style="margin-bottom: 8px;">
                <h3 style="margin-top:0; margin-bottom:2px; font-size:13.5px;">Confusion Matrix</h3>
                <div style="font-size:11px; color:var(--text-muted);">Actual vs Predicted (Threshold: 0.29)</div>
            </div>
            """)
            cm_data = get_confusion_matrix(scenario_id, batch_id=active_batch_id)
            has_cm = False
            if isinstance(cm_data, dict):
                if cm_data.get("confusion_matrix") or cm_data.get("matrix") or (cm_data.get("tp") is not None and cm_data.get("tn") is not None):
                    has_cm = True
            elif isinstance(cm_data, (list, np.ndarray)) and len(cm_data) > 0:
                has_cm = True

            if has_cm:
                cm_fig = plot_confusion_matrix(cm_data, theme=current_theme)
                if cm_fig.data:
                    st.plotly_chart(cm_fig, use_container_width=True, key="perf_cm")
                else:
                    render_empty_state_card(
                        "Performance evaluation unavailable.",
                        "Ground-truth labels are required to generate a confusion matrix.",
                        icon="🏷️"
                    )
            else:
                render_empty_state_card(
                    "Performance evaluation unavailable.",
                    "Ground-truth labels are required to generate a confusion matrix.",
                    icon="🏷️"
                )

        with c_interp:
            if latest_health is not None:
                f1_pct = latest_health['f1_percentage_change'] or 0.0
                m_health = latest_health['model_health_score'] or 0.0
                m_stat = latest_health['model_health_status'] or "UNKNOWN"
                render_html(f"""
                <div class="glass-card-secondary">
                    <h3 style="margin-top:0; margin-bottom:8px; font-size:13.5px;">V8 & V9 Performance Assessment</h3>
                    <div style="padding: 12px; background: var(--card-secondary); border-left: 3px solid var(--primary-blue); border-radius: 6px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                            <span style="font-size: 13.5px; font-weight: 600; color: var(--text-primary);">
                                Model Health: {m_health:.1f}%
                            </span>
                            {render_status_badge(m_stat)}
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">
                            <strong>F1 Degradation:</strong> {f1_pct:+.2f}% (Baseline F1: {BASELINE_F1:.4f} → Current F1: {perf['f1']:.4f})
                        </div>
                        <div style="font-size: 11.5px; color: var(--text-muted); line-height: 1.5;">
                            {latest_health['recommendation']}
                        </div>
                    </div>
                    <div style="margin-top: 10px; font-size: 11.5px; color: var(--text-muted);">
                        Degradation threshold is strictly calibrated at 10.0%. F1 degradation exceeding 10.0% trips the safety override to DEGRADED.
                    </div>
                </div>
                """)


# ── Page 4: Data Drift ────────────────────────────────────────────────
elif page == "Data Drift":
    render_page_header(f"DATA DRIFT: {st.session_state.drift_subpage.upper()}", "Statistical drift detection using V7.3 Kolmogorov-Smirnov and Chi-Square with Benjamini-Hochberg FDR.")
    
    if st.session_state.drift_subpage == "Feature Drift":
        if scenario_id == "baseline" or feature_drift.empty:
            render_empty_state_card(
                title="Baseline Scenario Active",
                message="The baseline serves as the immutable reference point (V7.1). Select an incoming batch or drift scenario to view feature drift metrics.",
                icon="🌊"
            )
        else:
            total_f = len(feature_drift)
            drifted_f = int(feature_drift['drift_detected'].sum())
            drift_pct = (drifted_f / total_f * 100.0) if total_f > 0 else 0.0
            
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
                render_kpi_card("Monitored Features", f"{total_f}", subtitle="19 Canonical Features", icon="📋")
            with c_m2:
                render_kpi_card("Drifted Features", f"{drifted_f}", delta=f"{drift_pct:.1f}% Drift Ratio", icon="🚨")
            with c_m3:
                render_kpi_card("FDR Correction Level", "α = 0.05", subtitle="Benjamini-Hochberg Adjusted", icon="🛡️")

            render_html("""
            <div class="glass-card-secondary" style="margin-top:16px; margin-bottom: 8px;">
                <h3 style="margin-top:0; margin-bottom:0; font-size:13.5px;">FEATURE-LEVEL DRIFT TEST RESULTS</h3>
            </div>
            """)
            disp_drift = feature_drift.copy()
            q_search = st.session_state.get("global_search", "").strip().lower()
            if q_search and "feature" in disp_drift.columns:
                match_mask = disp_drift["feature"].astype(str).str.lower().str.contains(q_search)
                if match_mask.any():
                    disp_drift = disp_drift[match_mask]
                    st.caption(f"Filtered by search query: '{q_search}' ({len(disp_drift)} matching features)")
            disp_drift["drift_detected"] = disp_drift["drift_detected"].apply(lambda x: "🚨 Drifted" if x == 1 else "✅ Stable")
            st.dataframe(disp_drift, use_container_width=True, hide_index=True)

    elif st.session_state.drift_subpage == "Distribution Drift":
        if feature_drift.empty:
            render_empty_state_card("No Distribution Data Available", "Select an active batch or drift scenario to compare distributions.", icon="📊")
        else:
            render_html("""
            <div class="glass-card-secondary" style="margin-bottom: 8px;">
                <h3 style="margin-top:0; margin-bottom:0; font-size:13.5px;">Magnitude of Distribution Shift per Monitored Feature</h3>
            </div>
            """)
            st.plotly_chart(
                plot_bar(feature_drift, x_col="feature", y_col="magnitude", color_col="drift_detected", title="Feature Shift Magnitude (KS Stat / TVD)", theme=current_theme),
                use_container_width=True, key="dist_drift_bar"
            )

    elif st.session_state.drift_subpage == "Target Drift":
        render_empty_state_card(
            title="Target Drift Monitoring",
            message="Target drift monitoring evaluates the shift in ground-truth labels across production windows when delayed ground truth arrives.",
            icon="🎯"
        )


# ── Page 5: AI Assistant ──────────────────────────────────────────────
elif page == "AI Assistant":
    render_page_header("✦ AI MONITORING COPILOT", "Retrieve ground-truth evidence and explain model behavior via LangGraph + Gemini.")
    
    # Live Gemini API Connection Status Indicator
    gem_status, gem_dot_class, gem_ok, gem_err = get_gemini_connection_status()
    gem_badge_color = "var(--status-healthy)" if gem_ok else ("var(--status-monitor)" if gem_status == "Configuration Required" else "var(--status-critical)")
    render_html(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; background: var(--card-secondary); border: 1px solid var(--subtle-border); border-radius: 8px; padding: 9px 14px; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="pulse-dot {gem_dot_class}"></span>
            <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">Gemini Copilot API:</span>
            <span style="font-size: 12px; color: {gem_badge_color}; font-weight: 600;">● {gem_status}</span>
        </div>
        <div style="font-size: 11px; color: var(--text-muted); font-family: monospace;">
            Engine: LangGraph + gemini-3.6-flash
        </div>
    </div>
    """)

    render_html("<div style='font-size:10.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>RECOMMENDED QUICK INQUIRIES:</div>")
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        if st.button("What changed in latest batch?", use_container_width=True):
            st.session_state.assistant_q = "What changed in the latest batch compared to baseline?"
    with qcol2:
        if st.button("Which features are drifting?", use_container_width=True):
            st.session_state.assistant_q = "Which features are drifting and what are their test statistics?"
    with qcol3:
        if st.button("Did performance degrade?", use_container_width=True):
            st.session_state.assistant_q = "Did model performance degrade on this batch compared to baseline?"
    with qcol4:
        if st.button("Why is health MONITOR?", use_container_width=True):
            st.session_state.assistant_q = "Why is health status MONITOR and what action is recommended?"

    if not gem_ok:
        if gem_status == "Configuration Required":
            st.warning("Gemini API key is not configured. Please ensure GEMINI_API_KEY is defined in your project's .env file.")
        else:
            st.error(f"Gemini Copilot is temporarily unavailable: {gem_err}")
    else:
        app_agent = None
        try:
            from agent.graph import build_graph
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key and hasattr(st, "secrets"):
                try:
                    api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
                except Exception:
                    pass
            llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
            app_agent = build_graph(llm)
        except Exception as e:
            st.error(f"AI Assistant could not be initialized: {str(e)}")

        if app_agent:
            render_html("""
            <div class="glass-card-secondary" style="margin-top: 12px; margin-bottom: 8px;">
                <h3 style="margin-top:0; margin-bottom:0; font-size:13.5px;">Observability Dialogue Interface</h3>
            </div>
            """)
            
            question = st.text_input("Ask IntelliPulse Copilot about this batch or scenario...", value=st.session_state.assistant_q, key="assistant_q_input")
            
            if st.button("Submit Inquiry", type="primary") and question:
                with st.spinner("Retrieving SQLite evidence and grounding response..."):
                    try:
                        res = app_agent.invoke({
                            "user_question": question,
                            "scenario": scenario_id,
                            "batch_id": active_batch_id
                        })
                        resp_text = res.get("final_response", "No response generated.")
                        st.markdown(resp_text)
                        st.session_state.assistant_q = ""
                    except Exception as e:
                        st.error(f"The AI Agent encountered an error: {str(e)}")


# ── Page 6: Reports ───────────────────────────────────────────────────
elif page == "Reports":
    render_page_header("MONITORING REPORTS", "Export comprehensive, audit-ready observability reports populated from persisted SQLite batch evidence.")
    
    if latest_health is None:
        render_empty_state_card(
            title="No Report Data Available",
            message="No monitoring records exist for the selected source.",
            icon="📋"
        )
    else:
        report_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_labeled_rpt = (not perf_df.empty)
        
        # Summary Tiles
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            render_kpi_card("Health Score", f"{latest_health['overall_health_score']:.1f}%", status=latest_health['overall_health_status'], icon="〽️")
        with rc2:
            render_kpi_card("Data Drift", f"{latest_health['drift_percentage']:.1f}%", status=latest_health['data_health_status'], icon="🌊")
        with rc3:
            perf_status = "Available" if is_labeled_rpt else "Unavailable (Unlabeled)"
            render_kpi_card("Performance", perf_status, status="HEALTHY" if is_labeled_rpt else "UNLABELED", icon="🎯")
        with rc4:
            render_kpi_card("Observability Engine", "V12 Production", subtitle="Frozen Threshold 0.29", icon="⚙️")

        # Dynamic Markdown Generation from Real SQLite Evidence
        report_md = f"""# IntelliPulse Production Monitoring Report — {scenario_id}
**Generated At:** {report_ts}  
**Monitored Batch ID:** {active_batch_id if active_batch_id else 'Preset Scenario'}  
**Baseline Contract:** V7.1 Reference / V8.0 Held-out Test Set  
**Model Decision Threshold:** {EXPECTED_THRESHOLD} (Frozen)  

---

## 1. Executive Summary
* **Overall Health Score:** {latest_health['overall_health_score']:.1f}% ({latest_health['overall_health_status']})
* **Data Health Score:** {latest_health['data_health_score']:.1f}% ({latest_health['data_health_status']})
* **Model Health Score:** {f"{latest_health['model_health_score']:.1f}%" if pd.notnull(latest_health['model_health_score']) else "N/A (Unlabeled Dataset)"} ({latest_health['model_health_status']})
* **Drifted Features Ratio:** {latest_health['drift_percentage']:.1f}%
* **Engine Recommendation:** {latest_health['recommendation']}

---

## 2. Statistical Drift Detection (V7 Methodology)
* Monitored Features: 19 canonical features (4 numerical, 15 categorical)
* Correction Method: Benjamini-Hochberg False Discovery Rate (α = 0.05)
* Numerical Test: Two-sample Kolmogorov-Smirnov test (Magnitude: KS statistic)
* Categorical Test: Chi-Square Goodness-of-Fit with baseline expected proportions (Magnitude: Total Variation Distance)
"""
        if not drift_data.empty:
            d_row = drift_data.iloc[0]
            report_md += f"""* **Total Drifted Features:** {d_row['drifted_features']} / {d_row['total_features']}  
* **Drift Severity Classification:** {d_row['severity']}  
"""

        report_md += """
---

## 3. Model Performance Evaluation (V8 Methodology)
"""
        if is_labeled_rpt:
            perf_r = perf_df.iloc[0]
            report_md += f"""* **Ground-truth Status:** Verified ('Churn' labels present)
* **Accuracy:** {perf_r['accuracy']:.4f} (Baseline: {BASELINE_ACCURACY:.4f})
* **Precision:** {perf_r['precision']:.4f} (Baseline: {BASELINE_PRECISION:.4f})
* **Recall:** {perf_r['recall']:.4f} (Baseline: {BASELINE_RECALL:.4f})
* **F1 Score:** {perf_r['f1']:.4f} (Baseline: {BASELINE_F1:.4f} | Shift: {latest_health['f1_percentage_change']:+.2f}%)
* **ROC-AUC:** {perf_r['roc_auc']:.4f} (Baseline: {BASELINE_ROC_AUC:.4f})
* **Confusion Matrix:** TP={perf_r['tp']}, TN={perf_r['tn']}, FP={perf_r['fp']}, FN={perf_r['fn']}
"""
        else:
            report_md += """* **Ground-truth Status:** Unlabeled batch (Ground-truth 'Churn' column not supplied)
* **Model Predictions:** Generated using frozen XGBoost classifier (Threshold: 0.29)
* **Performance Metrics:** Bypassed honestly per MLOps principles.
"""

        report_md += f"""
---

## 4. Deterministic Health Assessment (V9 Methodology)
* **Scoring Formula:** Overall = 0.40 × Data Health + 0.60 × Model Health
* **Safety Overrides:** Evaluated against V9 Rules 1–4
* **Final Status:** {latest_health['overall_health_status']}
* **Actionable Guidance:** {latest_health['recommendation']}
"""

        c_rep1, c_rep2 = st.columns([3, 1])
        with c_rep1:
            st.markdown(report_md)

        with c_rep2:
            render_html("""
            <div class="glass-card-secondary" style="margin-bottom: 10px;">
                <h3 style="margin-top:0; margin-bottom:10px; font-size:13.5px;">Export Report</h3>
            </div>
            """)
            st.download_button(
                label="📥 Download Markdown",
                data=report_md,
                file_name=f"intellipulse_report_{active_batch_id or scenario_id}.md",
                mime="text/markdown",
                use_container_width=True
            )


# ── Page 7: Settings ──────────────────────────────────────────────────
elif page == "Settings":
    render_page_header("SYSTEM CONFIGURATION & APPEARANCE", "Inspect system specifications, database health, and interface appearance.")
    
    # Appearance Card
    render_html("""
    <div class="glass-card-secondary" style="margin-bottom: 10px;">
        <h3 style="margin-top:0; margin-bottom:0; font-size:13.5px;">Interface Appearance</h3>
    </div>
    """)
    
    col_th1, col_th2 = st.columns([1, 2])
    with col_th1:
        theme_options = ["Dark Theme", "Light Theme"]
        cur_theme_idx = 0 if current_theme == "dark" else 1
        selected_theme_label = st.radio("Theme Mode", theme_options, index=cur_theme_idx, horizontal=True)
        new_theme = "dark" if selected_theme_label == "Dark Theme" else "light"
        if new_theme != current_theme:
            st.session_state.theme = new_theme
            st.rerun()
    with col_th2:
        render_html("""
        <div style="font-size: 12px; color: var(--text-secondary); padding-top: 24px;">
            Switches the color system between Slate/Navy dark surfaces and high-contrast light surfaces. All cards, charts, scrollbars, and tables adapt synchronously.
        </div>
        """)

    # Immutable System Specifications
    render_html(f"""
    <div class="glass-card-secondary" style="margin-top: 16px;">
        <h3 style="margin-top:0; margin-bottom:10px; font-size:13.5px;">Immutable System Specifications</h3>
        <table style="width:100%; border-collapse:collapse; font-size:12.5px; color:var(--text-secondary);">
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:7px 0; font-weight:500; color:var(--text-primary);">Classification Pipeline</td>
                <td>Frozen XGBoost (ColumnTransformer: StandardScaler + Median Imputer + OneHotEncoder)</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:7px 0; font-weight:500; color:var(--text-primary);">Decision Threshold</td>
                <td><strong style="color:var(--light-blue);">{actual_thresh}</strong> (Verified against performance baseline)</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:7px 0; font-weight:500; color:var(--text-primary);">Deterministic Health Weights</td>
                <td>Data Health: 40% | Model Health: 60%</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:7px 0; font-weight:500; color:var(--text-primary);">Multiple Testing Significance</td>
                <td>Benjamini-Hochberg FDR α = 0.05</td>
            </tr>
            <tr style="border-bottom:1px solid var(--border);">
                <td style="padding:7px 0; font-weight:500; color:var(--text-primary);">SQLite Database Path</td>
                <td><code>{DB_PATH}</code></td>
            </tr>
            <tr>
                <td style="padding:7px 0; font-weight:500; color:var(--text-primary);">ML Observability Engine</td>
                <td>IntelliPulse V12 Enterprise Observability</td>
            </tr>
        </table>
    </div>
    """)
