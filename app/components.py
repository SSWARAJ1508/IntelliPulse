import streamlit as st
import textwrap
from typing import Optional, List, Tuple

# Professional Geometric Navigation Icons (No emojis)
NAV_CONFIG = [
    ("Dashboard", "◉", "Dashboard", "System Overview & Key Metrics"),
    ("Live Monitor", "◫", "Live Monitor", "Incoming Batch Registry & Pipeline Signals"),
    ("Model Performance", "◇", "Model Performance", "Predictive Metrics & Confusion Matrix"),
    ("Data Drift", "◌", "Data Drift", "Feature & Distribution Drift Detection"),
    ("AI Assistant", "✦", "AI Assistant", "Gemini Observability Copilot"),
    ("Reports", "▣", "Reports", "Batch Reports & Export"),
    ("Settings", "⚙", "Settings", "System Specifications & Configuration")
]

def render_html(html_str: str):
    """
    Renders application-generated trusted HTML cleanly.
    Strips leading whitespace from every line to guarantee zero 4-space indentation,
    preventing Markdown parsers from interpreting indented lines as code blocks.
    """
    clean_html = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    st.markdown(clean_html, unsafe_allow_html=True)

def render_html_sidebar(html_str: str):
    """
    Renders trusted HTML inside the Streamlit sidebar with zero leading indentation.
    """
    clean_html = "\n".join(line.strip() for line in html_str.strip().splitlines() if line.strip())
    st.sidebar.markdown(clean_html, unsafe_allow_html=True)

def render_sidebar(actual_thresh: float = 0.29):
    """
    Renders the sidebar navigation cleanly separating Expanded and Collapsed states.
    In Collapsed state: renders ONLY icons with tooltips. Zero text in DOM.
    In Expanded state: renders full navigation with context panels.
    """
    is_collapsed = st.session_state.get("sidebar_collapsed", False)
    active_page = st.session_state.get("active_page", "Dashboard")

    # 1. Top Toggle Arrow (The ONLY navigation control in collapsed mode)
    toggle_icon = "→" if is_collapsed else "←"
    toggle_help = "Expand sidebar" if is_collapsed else "Collapse sidebar"
    
    if st.sidebar.button(toggle_icon, key="sidebar_toggle_arrow", help=toggle_help):
        st.session_state.sidebar_collapsed = not is_collapsed
        st.rerun()

    st.sidebar.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    # 2. Logo Header
    if not is_collapsed:
        render_html_sidebar("""
        <div style="padding: 2px 0 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="color:var(--primary-blue); font-size: 18px; font-weight: 700;">〽</span>
                <span style="font-weight: 700; font-size: 16px; letter-spacing: -0.01em; color: var(--text-primary);">IntelliPulse</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); letter-spacing: 0.04em; font-weight: 500; text-transform: uppercase; margin-top: 2px;">
                AI for Model Health
            </div>
        </div>
        """)
    else:
        render_html_sidebar("""
        <div style="text-align: center; padding: 2px 0 10px 0; border-bottom: 1px solid var(--border); margin-bottom: 10px;">
            <span style="color:var(--primary-blue); font-size: 18px; font-weight: 700;">〽</span>
        </div>
        """)

    # 3. Navigation Items
    if not is_collapsed:
        render_html_sidebar("<div style='font-size:10px; font-weight:600; color:var(--text-muted); margin-bottom:6px; text-transform:uppercase; letter-spacing: 0.06em;'>NAVIGATION</div>")
        for page_id, icon, label, desc in NAV_CONFIG:
            is_active = (page_id == active_page)
            btn_label = f"{icon}   {label}"
            btn_type = "primary" if is_active else "secondary"
            if st.sidebar.button(btn_label, key=f"nav_exp_{page_id}", type=btn_type, help=desc):
                st.session_state.active_page = page_id
                st.rerun()
                
            # Nested sub-nav for Data Drift
            if page_id == "Data Drift" and active_page == "Data Drift":
                st.sidebar.markdown("<div style='padding-left: 18px; margin: 2px 0 6px 0;'>", unsafe_allow_html=True)
                subpages = ["Feature Drift", "Distribution Drift", "Target Drift"]
                cur_sub = st.session_state.get("drift_subpage", "Feature Drift")
                for sub in subpages:
                    is_sub_active = (sub == cur_sub)
                    sub_label = f"• {sub}"
                    sub_type = "primary" if is_sub_active else "secondary"
                    if st.sidebar.button(sub_label, key=f"nav_sub_{sub}", type=sub_type):
                        st.session_state.drift_subpage = sub
                        st.rerun()
                st.sidebar.markdown("</div>", unsafe_allow_html=True)
    else:
        # Collapsed Mode: ONLY the icon is rendered in the button. ZERO text label in DOM.
        for page_id, icon, label, desc in NAV_CONFIG:
            is_active = (page_id == active_page)
            btn_type = "primary" if is_active else "secondary"
            if st.sidebar.button(icon, key=f"nav_col_{page_id}", type=btn_type, help=label):
                st.session_state.active_page = page_id
                st.rerun()

    # 4. Model Context & User Profile (Only in expanded mode)
    if not is_collapsed:
        st.sidebar.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        render_html_sidebar(f"""
        <div style="padding: 10px 12px; background: var(--card-secondary); border: 1px solid var(--subtle-border); border-radius: 8px; margin-bottom: 12px;">
            <div style='font-size:9.5px; font-weight:700; color:var(--text-muted); margin-bottom:6px; text-transform:uppercase; letter-spacing: 0.06em;'>MODEL CONTEXT</div>
            <div style="display:flex; justify-content:space-between; font-size: 11.5px; margin-bottom: 3px;">
                <span style="color:var(--text-muted);">Model</span>
                <span style="color:var(--text-primary); font-weight:500;">XGBoost (Frozen)</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size: 11.5px; margin-bottom: 3px;">
                <span style="color:var(--text-muted);">Threshold</span>
                <span style="color:var(--light-blue); font-weight:600;">{actual_thresh}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size: 11.5px; margin-bottom: 3px;">
                <span style="color:var(--text-muted);">Weights</span>
                <span style="color:var(--text-secondary);">0.40 / 0.60</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size: 11.5px;">
                <span style="color:var(--text-muted);">Observability</span>
                <span style="color:var(--status-healthy); font-weight:500;">V12 Production</span>
            </div>
        </div>
        """)

        render_html_sidebar("""
        <div style="padding: 8px 10px; border-top: 1px solid var(--border); display: flex; align-items: center; gap: 8px;">
            <div style="width: 26px; height: 26px; border-radius: 50%; background: var(--primary-blue); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 11px; color: white;">A</div>
            <div>
                <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">Shubham Swaraj</div>
                <div style="font-size: 10.5px; color: var(--text-muted);">Administrator</div>
            </div>
        </div>
        """)

def render_hero_banner(on_run_monitoring=None, on_view_reports=None):
    """
    Renders the calm, enterprise hero banner with neutral surfaces,
    written 'IntelliPulse'. Clean glassmorphic panel without wave background.
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        render_html("""
        <div class="hero-card animate-in delay-1">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap;">
                <span style="color: var(--primary-blue); font-size: 20px; font-weight: 700;">〽</span>
                <h1 style="margin: 0 !important; font-size: 22px !important; font-weight: 700; letter-spacing: -0.02em;">IntelliPulse</h1>
                <span style="background: rgba(37, 99, 235, 0.1); border: 1px solid rgba(37, 99, 235, 0.2); color: var(--light-blue); padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500;">AI for Model Health</span>
            </div>
            <p style="color: var(--text-secondary); margin: 6px 0 14px 0; font-size: 13px; line-height: 1.5; max-width: 680px;">
                Continuous visibility into data drift, model performance, and model health.
            </p>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <span style="background: var(--card-secondary); border: 1px solid var(--subtle-border); color: var(--text-secondary); padding: 3px 10px; border-radius: 14px; font-size: 11px;">Frozen XGBoost (0.29)</span>
                <span style="background: var(--card-secondary); border: 1px solid var(--subtle-border); color: var(--text-secondary); padding: 3px 10px; border-radius: 14px; font-size: 11px;">V7 KS & Chi-Square</span>
                <span style="background: var(--card-secondary); border: 1px solid var(--subtle-border); color: var(--text-secondary); padding: 3px 10px; border-radius: 14px; font-size: 11px;">V9 Deterministic Health</span>
                <span style="background: var(--status-healthy-bg); border: 1px solid var(--status-healthy-border); color: var(--status-healthy); padding: 3px 10px; border-radius: 14px; font-size: 11px;">Gemini Copilot</span>
            </div>
        </div>
        """)
    with col2:
        with st.container():
            st.markdown('<span class="glass-wrapper"></span>', unsafe_allow_html=True)
            render_html("""
            <div style="font-size: 10.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                QUICK ACTIONS
            </div>
            """)
            if st.button("Run Monitoring", type="primary", use_container_width=True, key="hero_run_btn"):
                if on_run_monitoring:
                    on_run_monitoring()
            if st.button("View Reports", use_container_width=True, key="hero_reports_btn"):
                st.session_state.active_page = "Reports"
                st.rerun()

def render_status_badge(status: str) -> str:
    """Generates standardized HTML badge for any monitoring state."""
    stat_clean = str(status).upper().replace(" ", "_")
    return f'<span class="status-badge {stat_clean}">{status}</span>'

def render_kpi_card(title: str, value: str, status: Optional[str] = None,
                    delta: Optional[str] = None, delta_label: Optional[str] = None,
                    icon: str = "✦", level: str = "secondary",
                    subtitle: Optional[str] = None):
    """
    Renders a calm, enterprise KPI tile.
    Values are neutral white (in dark) or neutral dark (in light).
    """
    card_class = f"glass-card-{level}" if level in ["primary", "secondary", "tertiary"] else "glass-card"
    status_html = f"<div>{render_status_badge(status)}</div>" if status else ""
    
    delta_html = ""
    if delta is not None:
        delta_str = str(delta)
        delta_class = "positive" if (delta_str.startswith("+") or "gain" in delta_str.lower()) else "negative" if delta_str.startswith("-") else "neutral"
        label_str = f" <span style='color: var(--text-muted); font-size: 11px;'>{delta_label}</span>" if delta_label else ""
        delta_html = f'<div class="kpi-footer"><span class="kpi-delta {delta_class}">{delta_str}</span>{label_str}</div>'
    elif subtitle:
        delta_html = f'<div class="kpi-footer" style="color: var(--text-muted);">{subtitle}</div>'

    html = (
        f'<div class="{card_class} kpi-card animate-in delay-2">'
        f'<div class="kpi-header">'
        f'<div class="kpi-title">{title}</div>'
        f'<div class="kpi-icon">{icon}</div>'
        f'</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{status_html}'
        f'{delta_html}'
        f'</div>'
    )
    render_html(html)

def render_metadata_strip(items: List[Tuple[str, str, Optional[str]]]):
    """
    Renders a secondary card strip for displaying batch metadata.
    items: List of (Label, Value, Optional Color)
    """
    cells = []
    for label, val, color in items:
        color_style = f"color: {color};" if color else "color: var(--text-primary);"
        cells.append(
            f'<div>'
            f'<div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">{label}</div>'
            f'<div style="font-weight: 500; font-size: 12.5px; {color_style}">{val}</div>'
            f'</div>'
        )

    html = (
        f'<div class="glass-card-tertiary animate-in delay-1" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">'
        f'{"".join(cells)}'
        f'</div>'
    )
    render_html(html)

def render_pipeline_timeline(current_stage: str = "COMPLETED"):
    """
    Renders an end-to-end processing pipeline tracker for Live Monitor:
    Upload → Schema Validation → Drift Detection → Model Inference → Health Assessment → Completed
    """
    stages = [
        ("Upload", "CSV Ingested"),
        ("Validation", "Schema & Quality"),
        ("Drift", "V7 KS & Chi-Square"),
        ("Inference", "XGBoost (Thr: 0.29)"),
        ("Health", "V9 Deterministic"),
        ("Completed", "Persisted in SQLite")
    ]
    
    cur_upper = current_stage.upper()
    cur_idx = len(stages) - 1
    for idx, (sname, _) in enumerate(stages):
        if sname.upper() == cur_upper:
            cur_idx = idx
            break
            
    pills = []
    for idx, (name, desc) in enumerate(stages):
        if cur_upper == "FAILED" and idx == cur_idx:
            state_color = "var(--status-critical)"
            icon = "✗"
            pill_bg = "var(--status-critical-bg)"
            border = "1px solid var(--status-critical-border)"
        elif idx <= cur_idx:
            state_color = "var(--status-healthy)"
            icon = "✓"
            pill_bg = "var(--status-healthy-bg)"
            border = "1px solid var(--status-healthy-border)"
        else:
            state_color = "var(--text-disabled)"
            icon = "○"
            pill_bg = "var(--card-secondary)"
            border = "1px solid var(--subtle-border)"
            
        pills.append(
            f'<div style="flex: 1; min-width: 135px; background: {pill_bg}; border: {border}; border-radius: 8px; padding: 8px 10px;">'
            f'<div style="display: flex; align-items: center; gap: 5px; margin-bottom: 2px;">'
            f'<span style="color: {state_color}; font-weight: 700; font-size: 12px;">{icon}</span>'
            f'<span style="font-weight: 600; font-size: 12px; color: var(--text-primary);">{name}</span>'
            f'</div>'
            f'<div style="font-size: 10.5px; color: var(--text-muted);">{desc}</div>'
            f'</div>'
        )

    html = (
        f'<div class="glass-card-secondary animate-in delay-2" style="margin-bottom: 18px;">'
        f'<div style="font-size: 10.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px; font-weight: 600;">'
        f'PIPELINE EXECUTION STAGE TRACKER'
        f'</div>'
        f'<div style="display: flex; gap: 8px; flex-wrap: wrap;">'
        f'{"".join(pills)}'
        f'</div>'
        f'</div>'
    )
    render_html(html)

def render_empty_state_card(title: str, message: str, icon: str = "📭", reason: Optional[str] = None):
    """
    Honest empty state for unlabeled batches or missing data.
    """
    reason_html = (
        f'<div style="margin-top: 10px; padding: 8px 12px; background: var(--card-secondary); border: 1px solid var(--subtle-border); border-radius: 6px; font-size: 11.5px; color: var(--text-secondary); max-width: 480px; margin-left: auto; margin-right: auto;">'
        f'{reason}'
        f'</div>'
    ) if reason else ""

    html = (
        f'<div class="glass-card-secondary animate-in delay-2" style="text-align: center; padding: 32px 20px;">'
        f'<div style="font-size: 28px; margin-bottom: 8px;">{icon}</div>'
        f'<h3 style="margin-bottom: 4px !important; color: var(--text-primary);">{title}</h3>'
        f'<p style="color: var(--text-secondary); font-size: 13px; max-width: 520px; margin: 0 auto; line-height: 1.5;">{message}</p>'
        f'{reason_html}'
        f'</div>'
    )
    render_html(html)
