import streamlit as st

def apply_custom_styles(theme: str = "dark", sidebar_collapsed: bool = False):
    """
    Returns enterprise-grade CSS tokens and styles for dark and light modes.
    Includes clean glassmorphic panels and full mobile responsiveness.
    """
    is_dark = (theme != "light")
    sidebar_width = "72px" if sidebar_collapsed else "260px"

    # Exact Enterprise Color Specifications
    if is_dark:
        bg_base = "#0F172A"
        bg_sidebar = "#111827"
        bg_navbar = "#111827"
        card_primary = "#1E293B"
        card_secondary = "#172235"
        card_hover = "#243247"
        border = "#334155"
        subtle_border = "rgba(148, 163, 184, 0.15)"
        text_primary = "#F8FAFC"
        text_secondary = "#CBD5E1"
        text_muted = "#94A3B8"
        text_disabled = "#64748B"
        primary_blue = "#2563EB"
        primary_blue_hover = "#1D4ED8"
        light_blue = "#60A5FA"
        btn_secondary_bg = "#334155"
        btn_secondary_text = "#F8FAFC"
        btn_secondary_hover = "#3E4F66"
        glass_bg = "rgba(30, 41, 59, 0.75)"
        glass_border = "rgba(148, 163, 184, 0.12)"
        shadow_card = "0 8px 24px rgba(0, 0, 0, 0.18)"
        shadow_card_hover = "0 12px 30px rgba(0, 0, 0, 0.24)"
        scrollbar_track = "#0F172A"
        scrollbar_thumb = "#475569"
        scrollbar_thumb_hover = "#64748B"
        input_bg = "#111827"
        table_bg = "#1E293B"
    else:
        bg_base = "#F8FAFC"
        bg_sidebar = "#FFFFFF"
        bg_navbar = "#FFFFFF"
        card_primary = "#FFFFFF"
        card_secondary = "#F8FAFC"
        card_hover = "#F1F5F9"
        border = "#E2E8F0"
        subtle_border = "#CBD5E1"
        text_primary = "#0F172A"
        text_secondary = "#475569"
        text_muted = "#64748B"
        text_disabled = "#94A3B8"
        primary_blue = "#2563EB"
        primary_blue_hover = "#1D4ED8"
        light_blue = "#2563EB"
        btn_secondary_bg = "#E2E8F0"
        btn_secondary_text = "#0F172A"
        btn_secondary_hover = "#CBD5E1"
        glass_bg = "rgba(255, 255, 255, 0.80)"
        glass_border = "rgba(15, 23, 42, 0.08)"
        shadow_card = "0 4px 16px rgba(15, 23, 42, 0.06)"
        shadow_card_hover = "0 8px 24px rgba(15, 23, 42, 0.10)"
        scrollbar_track = "#F1F5F9"
        scrollbar_thumb = "#CBD5E1"
        scrollbar_thumb_hover = "#94A3B8"
        input_bg = "#FFFFFF"
        table_bg = "#FFFFFF"

    # Semantic Status Colors (Exclusively for health metrics and alerts)
    status_healthy = "#16A34A"
    status_healthy_bg = "rgba(22, 163, 74, 0.12)"
    status_healthy_border = "rgba(22, 163, 74, 0.25)"

    status_monitor = "#D97706"
    status_monitor_bg = "rgba(217, 119, 6, 0.12)"
    status_monitor_border = "rgba(217, 119, 6, 0.25)"

    status_investigate = "#EA580C"
    status_investigate_bg = "rgba(234, 88, 12, 0.12)"
    status_investigate_border = "rgba(234, 88, 12, 0.25)"

    status_critical = "#DC2626"
    status_critical_bg = "rgba(220, 38, 38, 0.12)"
    status_critical_border = "rgba(220, 38, 38, 0.25)"

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        :root {{
            --bg-base: {bg_base};
            --bg-sidebar: {bg_sidebar};
            --bg-navbar: {bg_navbar};
            
            --card-primary: {card_primary};
            --card-secondary: {card_secondary};
            --card-hover: {card_hover};
            
            --border: {border};
            --subtle-border: {subtle_border};
            --glass-bg: {glass_bg};
            --glass-border: {glass_border};
            
            --text-primary: {text_primary};
            --text-secondary: {text_secondary};
            --text-muted: {text_muted};
            --text-disabled: {text_disabled};
            
            --primary-blue: {primary_blue};
            --primary-blue-hover: {primary_blue_hover};
            --light-blue: {light_blue};
            
            --status-healthy: {status_healthy};
            --status-healthy-bg: {status_healthy_bg};
            --status-healthy-border: {status_healthy_border};
            
            --status-monitor: {status_monitor};
            --status-monitor-bg: {status_monitor_bg};
            --status-monitor-border: {status_monitor_border};
            
            --status-investigate: {status_investigate};
            --status-investigate-bg: {status_investigate_bg};
            --status-investigate-border: {status_investigate_border};
            
            --status-critical: {status_critical};
            --status-critical-bg: {status_critical_bg};
            --status-critical-border: {status_critical_border};
            
            --shadow-card: {shadow_card};
            --shadow-card-hover: {shadow_card_hover};
        }}

        /* ── Base Page Reset ────────────────────────────────────────────── */
        html, body, .stApp {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            color: var(--text-primary) !important;
            background-color: var(--bg-base) !important;
            overflow-x: hidden !important;
            max-width: 100vw !important;
            width: 100% !important;
        }}

        .block-container {{
            padding-top: 1.2rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 100% !important;
            width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            box-sizing: border-box !important;
            overflow-x: hidden !important;
        }}

        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        [data-testid="stToolbar"] {{ visibility: hidden; }}
        [data-testid="stDecoration"] {{ display: none; }}
        header[data-testid="stHeader"] {{
            background: transparent !important;
            color: var(--text-primary) !important;
            height: 2.75rem !important;
            z-index: 99999 !important;
        }}
        /* Suppress Streamlit's native sidebar collapse controls.
           Sidebar collapsing is exclusively managed by the custom arrow control (sidebar_toggle_arrow) */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"] {{
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        [data-testid="stSidebarHeader"] {{
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }}

        /* ── Custom Scrollbar ────────────────────────────────────────────── */
        ::-webkit-scrollbar {{
            width: 7px;
            height: 7px;
        }}
        ::-webkit-scrollbar-track {{
            background: {scrollbar_track};
        }}
        ::-webkit-scrollbar-thumb {{
            background: {scrollbar_thumb};
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: {scrollbar_thumb_hover};
        }}

        /* ── Typography Scale ───────────────────────────────────────────── */
        h1, h2, h3, h4 {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            letter-spacing: -0.015em !important;
            font-weight: 600 !important;
        }}
        h1 {{
            font-size: 24px !important;
            line-height: 1.2 !important;
            color: var(--text-primary) !important;
            margin-bottom: 12px !important;
        }}
        h2 {{
            font-size: 17px !important;
            color: var(--text-primary) !important;
            margin-bottom: 10px !important;
        }}
        h3 {{
            font-size: 13.5px !important;
            font-weight: 600 !important;
            color: var(--text-secondary) !important;
            margin-bottom: 8px !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        p, label {{
            color: var(--text-secondary);
        }}

        /* ── Calm Cards Hierarchy ───────────────────────────────────────── */
        .glass-card, .glass-card-primary, .glass-card-secondary {{
            background: var(--card-primary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px 20px;
            box-shadow: var(--shadow-card);
            transition: transform 200ms ease-out, box-shadow 200ms ease-out, background 200ms ease-out;
            margin-bottom: 16px;
            position: relative;
        }}

        .glass-card:hover, .glass-card-primary:hover, .glass-card-secondary:hover {{
            transform: translateY(-2px);
            background: var(--card-hover);
            box-shadow: var(--shadow-card-hover);
        }}

        .glass-card-tertiary {{
            background: var(--card-secondary);
            border: 1px solid var(--subtle-border);
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 14px;
        }}

        /* ── Clean Hero Panel ───────────────────────────────────────────── */
        .hero-card {{
            background: var(--card-primary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 22px 24px;
            margin-bottom: 16px;
            box-shadow: var(--shadow-card);
            transition: transform 200ms ease-out, box-shadow 200ms ease-out;
        }}
        .hero-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-card-hover);
        }}

        /* Streamlit vertical block card adapter */
        div[data-testid="stVerticalBlock"]:has(> div > div > div > div > .glass-wrapper) {{
            background: var(--card-primary) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 18px 20px !important;
            box-shadow: var(--shadow-card) !important;
            transition: transform 200ms ease-out, box-shadow 200ms ease-out !important;
            margin-bottom: 16px !important;
        }}
        div[data-testid="stVerticalBlock"]:has(> div > div > div > div > .glass-wrapper):hover {{
            transform: translateY(-2px) !important;
            background: var(--card-hover) !important;
            box-shadow: var(--shadow-card-hover) !important;
        }}

        /* ── KPI Cards ──────────────────────────────────────────────────── */
        .kpi-card {{
            padding: 16px 18px;
            text-align: left;
        }}
        .kpi-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .kpi-title {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .kpi-icon {{
            font-size: 14px;
            color: var(--light-blue);
        }}
        .kpi-value {{
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
            line-height: 1.15;
            margin-bottom: 4px;
        }}
        .kpi-footer {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11.5px;
        }}
        .kpi-delta {{
            font-weight: 600;
        }}
        .kpi-delta.positive {{ color: var(--status-healthy); }}
        .kpi-delta.negative {{ color: var(--status-critical); }}
        .kpi-delta.neutral {{ color: var(--text-muted); }}

        /* ── Status Badges (Semantic Only) ──────────────────────────────── */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 10.5px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            line-height: 1.2;
        }}
        .status-badge.HEALTHY, .status-badge.COMPLETED, .status-badge.CONNECTED {{
            background: var(--status-healthy-bg);
            color: var(--status-healthy);
            border: 1px solid var(--status-healthy-border);
        }}
        .status-badge.MONITOR, .status-badge.WARNING, .status-badge.CONFIGURATION_REQUIRED {{
            background: var(--status-monitor-bg);
            color: var(--status-monitor);
            border: 1px solid var(--status-monitor-border);
        }}
        .status-badge.INVESTIGATE, .status-badge.PROCESSING, .status-badge.VALIDATING {{
            background: var(--status-investigate-bg);
            color: var(--status-investigate);
            border: 1px solid var(--status-investigate-border);
        }}
        .status-badge.CRITICAL, .status-badge.FAILED, .status-badge.TEMPORARILY_UNAVAILABLE {{
            background: var(--status-critical-bg);
            color: var(--status-critical);
            border: 1px solid var(--status-critical-border);
        }}
        .status-badge.UNLABELED, .status-badge.INSUFFICIENT_EVIDENCE {{
            background: rgba(148, 163, 184, 0.1);
            color: var(--text-muted);
            border: 1px solid var(--subtle-border);
        }}

        /* ── Status Pulse Dot ───────────────────────────────────────────── */
        .pulse-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
        }}
        .pulse-dot.online {{
            background-color: var(--status-healthy);
        }}
        .pulse-dot.warning {{
            background-color: var(--status-monitor);
        }}
        .pulse-dot.critical {{
            background-color: var(--status-critical);
        }}

        /* ── Clean Navbar ───────────────────────────────────────────────── */
        .glass-navbar {{
            background: var(--bg-navbar);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px 16px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--shadow-card);
            flex-wrap: wrap;
            gap: 8px;
        }}

        .topnav-search,
        div[data-testid="stHorizontalBlock"] div[data-testid="stTextInput"] input {{
            width: 100% !important;
            background: var(--bg-base) !important;
            border: 1px solid var(--subtle-border) !important;
            padding: 6px 12px !important;
            border-radius: 6px !important;
            color: var(--text-primary) !important;
            font-size: 12.5px !important;
            outline: none !important;
            transition: border-color 150ms ease !important;
            font-family: inherit !important;
            min-height: 34px !important;
            height: 34px !important;
        }}
        .topnav-search:focus,
        div[data-testid="stHorizontalBlock"] div[data-testid="stTextInput"] input:focus {{
            border-color: var(--primary-blue) !important;
            box-shadow: 0 0 0 1px var(--primary-blue) !important;
        }}
        div[data-testid="stHorizontalBlock"] div[data-testid="stTextInput"] {{
            margin-bottom: 0 !important;
        }}

        /* ── Global Search Results System ────────────────────────────────── */
        .search-results-box {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px 20px;
            margin: 12px 0 16px 0;
            box-shadow: var(--shadow-card);
        }}
        .search-result-item {{
            background: var(--card-secondary);
            border: 1px solid var(--subtle-border);
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .search-badge {{
            font-size: 10.5px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 3px 8px;
            border-radius: 4px;
        }}

        /* ── Sidebar System (Strict 260px / 72px) ────────────────────────── */
        [data-testid="stSidebar"] {{
            background-color: var(--bg-sidebar) !important;
            border-right: 1px solid var(--border) !important;
            width: {sidebar_width} !important;
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
            box-shadow: none !important;
            transform: none !important;
            margin-left: 0 !important;
            display: block !important;
            visibility: visible !important;
            transition: width 280ms ease-in-out, min-width 280ms ease-in-out, max-width 280ms ease-in-out !important;
            overflow-x: hidden !important;
        }}

        [data-testid="stSidebar"][aria-expanded="false"] {{
            transform: none !important;
            margin-left: 0 !important;
            display: block !important;
            visibility: visible !important;
            width: {sidebar_width} !important;
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            padding: {'12px 6px' if sidebar_collapsed else '16px 12px'} !important;
            overflow-x: hidden !important;
        }}

        /* Sidebar Navigation Buttons */
        [data-testid="stSidebar"] .stButton > button {{
            width: 100% !important;
            border-radius: 6px !important;
            padding: {'8px 0' if sidebar_collapsed else '7px 10px'} !important;
            font-size: {'15px' if sidebar_collapsed else '12.5px'} !important;
            font-weight: 500 !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            color: var(--text-muted) !important;
            transition: all 150ms ease-out !important;
            display: flex !important;
            justify-content: {'center' if sidebar_collapsed else 'flex-start'} !important;
            align-items: center !important;
        }}
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button span {{
            color: var(--text-muted) !important;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(148, 163, 184, 0.08) !important;
            color: var(--text-primary) !important;
            transform: none !important;
        }}
        [data-testid="stSidebar"] .stButton > button:hover p,
        [data-testid="stSidebar"] .stButton > button:hover span {{
            color: var(--text-primary) !important;
        }}

        /* Active Navigation Item (Coherent Light / Dark Styling) */
        [data-testid="stSidebar"] .stButton > button[kind="primary"],
        [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {{
            background: {'rgba(37, 99, 235, 0.12)' if is_dark else 'rgba(37, 99, 235, 0.10)'} !important;
            background-color: {'rgba(37, 99, 235, 0.12)' if is_dark else 'rgba(37, 99, 235, 0.10)'} !important;
            border: 1px solid {'rgba(37, 99, 235, 0.35)' if is_dark else 'rgba(37, 99, 235, 0.25)'} !important;
            color: {'#60A5FA' if is_dark else '#1D4ED8'} !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }}
        [data-testid="stSidebar"] .stButton > button[kind="primary"] p,
        [data-testid="stSidebar"] .stButton > button[kind="primary"] span,
        [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] p,
        [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] span {{
            color: {'#60A5FA' if is_dark else '#1D4ED8'} !important;
            font-weight: 600 !important;
        }}


        @media (min-width: 992px) {{
            [data-testid="stSidebar"] {{
                display: block !important;
                visibility: visible !important;
                transform: none !important;
                margin-left: 0 !important;
            }}
        }}

        /* ── Standard Professional Buttons ──────────────────────────────── */
        .stButton > button {{
            background: {btn_secondary_bg} !important;
            background-color: {btn_secondary_bg} !important;
            border: 1px solid var(--subtle-border) !important;
            color: {btn_secondary_text} !important;
            border-radius: 8px !important;
            padding: 7px 14px !important;
            font-weight: 500 !important;
            font-size: 13px !important;
            transition: background 180ms ease, border-color 180ms ease !important;
            box-shadow: none !important;
        }}
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {{
            color: {btn_secondary_text} !important;
            font-weight: 500 !important;
        }}
        .stButton > button:hover {{
            background: {btn_secondary_hover} !important;
            background-color: {btn_secondary_hover} !important;
            color: var(--text-primary) !important;
            transform: none !important;
        }}
        .stButton > button:hover p,
        .stButton > button:hover span,
        .stButton > button:hover div {{
            color: var(--text-primary) !important;
        }}

        /* ── CRITICAL: PRIMARY BUTTON WHITE TEXT IN ALL THEMES ──────────── */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {{
            background: var(--primary-blue) !important;
            background-color: var(--primary-blue) !important;
            border: 1px solid var(--primary-blue) !important;
            color: #FFFFFF !important;
            box-shadow: none !important;
        }}
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span,
        .stButton > button[kind="primary"] div,
        .stButton > button[data-testid="baseButton-primary"] p,
        .stButton > button[data-testid="baseButton-primary"] span,
        .stButton > button[data-testid="baseButton-primary"] div {{
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }}
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {{
            background: var(--primary-blue-hover) !important;
            background-color: var(--primary-blue-hover) !important;
            border-color: var(--primary-blue-hover) !important;
            color: #FFFFFF !important;
            transform: none !important;
        }}
        .stButton > button[kind="primary"]:hover p,
        .stButton > button[kind="primary"]:hover span,
        .stButton > button[kind="primary"]:hover div,
        .stButton > button[data-testid="baseButton-primary"]:hover p,
        .stButton > button[data-testid="baseButton-primary"]:hover span,
        .stButton > button[data-testid="baseButton-primary"]:hover div {{
            color: #FFFFFF !important;
        }}
        .stButton > button[kind="primary"]:active,
        .stButton > button[data-testid="baseButton-primary"]:active {{
            background: #1E40AF !important;
            background-color: #1E40AF !important;
            border-color: #1E40AF !important;
            color: #FFFFFF !important;
        }}
        .stButton > button[kind="primary"]:active p,
        .stButton > button[kind="primary"]:active span,
        .stButton > button[kind="primary"]:active div,
        .stButton > button[data-testid="baseButton-primary"]:active p,
        .stButton > button[data-testid="baseButton-primary"]:active span,
        .stButton > button[data-testid="baseButton-primary"]:active div {{
            color: #FFFFFF !important;
        }}
        .stButton > button[disabled],
        .stButton > button[disabled] p,
        .stButton > button[disabled] span {{
            background: var(--card-secondary) !important;
            color: var(--text-disabled) !important;
            border-color: var(--subtle-border) !important;
            cursor: not-allowed !important;
        }}

        /* ── Form Inputs & Selectboxes ──────────────────────────────────── */
        .stSelectbox > div > div {{
            background-color: {input_bg} !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 6px !important;
            font-size: 12.5px !important;
        }}
        .stTextInput > div > div > input {{
            background-color: {input_bg} !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 6px !important;
            font-size: 12.5px !important;
        }}
        .stTextInput > div > div > input:focus {{
            border-color: var(--primary-blue) !important;
            box-shadow: 0 0 0 1px var(--primary-blue) !important;
        }}

        /* ── Data Tables & Dataframes ───────────────────────────────────── */
        div[data-testid="stDataFrame"] {{
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
            background: {table_bg} !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            width: 100% !important;
            max-width: 100% !important;
        }}

        /* ── Subtle Scroll Reveal Animation ─────────────────────────────── */
        @media (prefers-reduced-motion: no-preference) {{
            .animate-in {{
                animation: subtleReveal 0.35s ease-out forwards;
                opacity: 0;
                transform: translateY(6px);
            }}
            .delay-1 {{ animation-delay: 20ms; }}
            .delay-2 {{ animation-delay: 40ms; }}
            .delay-3 {{ animation-delay: 80ms; }}
            
            @keyframes subtleReveal {{
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
        }}

        @keyframes intellipulse-progress {{
            0% {{
                transform: translateX(-100%);
            }}
            50% {{
                transform: translateX(0%);
            }}
            100% {{
                transform: translateX(100%);
            }}
        }}

        /* ── Multi-Breakpoint Responsive Layout ─────────────────────────── */
        /* 1440px Desktop */
        @media (max-width: 1440px) {{
            .block-container {{
                padding-left: 1.75rem !important;
                padding-right: 1.75rem !important;
            }}
        }}

        /* 1280px Desktop */
        @media (max-width: 1280px) {{
            .block-container {{
                padding-left: 1.5rem !important;
                padding-right: 1.5rem !important;
            }}
            .glass-navbar {{
                padding: 8px 14px !important;
            }}
        }}

        /* 1100px Laptop */
        @media (max-width: 1100px) {{
            .block-container {{
                padding-left: 1.25rem !important;
                padding-right: 1.25rem !important;
            }}
            div[data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
                gap: 12px 10px !important;
            }}
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                min-width: 180px !important;
            }}
            .kpi-card {{
                padding: 14px 16px !important;
            }}
            .kpi-value {{
                font-size: 23px !important;
            }}
        }}

        /* 1024px Compact Laptop */
        @media (max-width: 1024px) {{
            .block-container {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }}
            /* Stack Hero quick actions neatly if needed */
            div[data-testid="stHorizontalBlock"]:has(.hero-card) > div[data-testid="column"] {{
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }}
            .glass-navbar {{
                padding: 8px 12px !important;
            }}
        }}

        /* 900px Narrow Desktop / Tablet Landscape */
        @media (max-width: 900px) {{
            .block-container {{
                padding-left: 0.85rem !important;
                padding-right: 0.85rem !important;
            }}
            div[data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
                gap: 10px 8px !important;
            }}
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                flex: 1 1 calc(50% - 8px) !important;
                min-width: 160px !important;
            }}
            .kpi-value {{
                font-size: 21px !important;
            }}
            .glass-card, .glass-card-primary, .glass-card-secondary, .hero-card {{
                padding: 16px 18px !important;
                margin-bottom: 12px !important;
            }}
        }}

        /* 768px Tablet Portrait */
        @media (max-width: 768px) {{
            .block-container {{
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 3.2rem !important;
                padding-bottom: 2rem !important;
                max-width: 100vw !important;
                box-sizing: border-box !important;
            }}

            /* Column Wrapping for Tablet */
            div[data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
                gap: 12px 8px !important;
            }}
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                flex: 1 1 calc(50% - 8px) !important;
                min-width: 180px !important;
            }}

            /* Top Navbar Action Cluster: Keep operational pill, theme toggle, and run button on one row */
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) {{
                flex-wrap: nowrap !important;
                gap: 6px !important;
                align-items: center !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) > div[data-testid="column"]:nth-child(1) {{
                flex: 0 0 auto !important;
                min-width: auto !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) > div[data-testid="column"]:nth-child(2) {{
                flex: 0 0 38px !important;
                min-width: 38px !important;
                max-width: 38px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) > div[data-testid="column"]:nth-child(3) {{
                flex: 1 1 auto !important;
                min-width: 110px !important;
            }}

            /* Mobile Sidebar Drawer */
            [data-testid="stSidebar"] {{
                width: 84vw !important;
                min-width: 260px !important;
                max-width: 320px !important;
                box-shadow: 0 0 24px rgba(0, 0, 0, 0.45) !important;
                z-index: 999999 !important;
                -webkit-overflow-scrolling: touch !important;
            }}
            section[data-testid="stSidebar"] .stButton > button {{
                min-height: 42px !important;
                padding: 9px 12px !important;
                font-size: 13px !important;
            }}

            /* Typography */
            h1 {{
                font-size: 19px !important;
                line-height: 1.25 !important;
                margin-bottom: 8px !important;
            }}
            h2 {{
                font-size: 16px !important;
                margin-bottom: 8px !important;
            }}
            h3 {{
                font-size: 12.5px !important;
            }}

            /* Cards */
            .glass-card, .glass-card-primary, .glass-card-secondary, .hero-card {{
                padding: 14px 14px 16px 14px !important;
                margin-bottom: 12px !important;
                border-radius: 10px !important;
                box-sizing: border-box !important;
                max-width: 100% !important;
            }}

            /* 2-Column KPI Card Grid on Mobile */
            div[data-testid="stHorizontalBlock"]:has(.kpi-card) {{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: wrap !important;
                gap: 8px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.kpi-card) > div[data-testid="column"] {{
                flex: 1 1 calc(50% - 4px) !important;
                min-width: 140px !important;
                max-width: calc(50% - 4px) !important;
            }}
            .kpi-card {{
                padding: 11px 12px !important;
                min-height: 84px !important;
            }}
            .kpi-value {{
                font-size: 20px !important;
            }}
            .kpi-title {{
                font-size: 11px !important;
            }}

            .glass-card-tertiary {{
                padding: 10px 12px !important;
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 8px !important;
                word-break: break-word !important;
                overflow-wrap: break-word !important;
            }}

            /* Responsive tables, code blocks, and Plotly charts */
            div[data-testid="stDataFrame"], div.js-plotly-plot, .plot-container {{
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
            }}
            pre, code {{
                word-break: break-all !important;
                white-space: pre-wrap !important;
            }}

            /* Search Results Bar */
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="clear_search_btn"]) {{
                display: flex !important;
                flex-wrap: wrap !important;
                align-items: center !important;
                gap: 8px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="clear_search_btn"]) > div[data-testid="column"]:first-child {{
                flex: 1 1 calc(100% - 120px) !important;
                min-width: 180px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="clear_search_btn"]) > div[data-testid="column"]:last-child {{
                flex: 0 0 110px !important;
                min-width: 110px !important;
            }}
        }}

        /* 480px Mobile Phone */
        @media (max-width: 480px) {{
            .block-container {{
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                padding-top: 3.1rem !important;
                padding-bottom: 2rem !important;
            }}
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }}
            /* Retain 2-column KPI cards on phones */
            div[data-testid="stHorizontalBlock"]:has(.kpi-card) > div[data-testid="column"] {{
                flex: 1 1 calc(50% - 4px) !important;
                min-width: 135px !important;
                max-width: calc(50% - 4px) !important;
            }}
            /* Search + Scenario row on phones: side by side if >= 340px */
            div[data-testid="stHorizontalBlock"]:has(input[data-testid*="global_search_input"]) > div[data-testid="column"] {{
                flex: 1 1 calc(50% - 4px) !important;
                min-width: 130px !important;
            }}
            /* Retain single-row navbar action cluster on phones */
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) {{
                flex-wrap: nowrap !important;
                gap: 4px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) > div[data-testid="column"]:nth-child(1) {{
                flex: 0 0 auto !important;
                min-width: auto !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) > div[data-testid="column"]:nth-child(2) {{
                flex: 0 0 36px !important;
                min-width: 36px !important;
                max-width: 36px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(button[data-testid*="navbar_theme_toggle_btn"]) > div[data-testid="column"]:nth-child(3) {{
                flex: 1 1 auto !important;
                min-width: 95px !important;
            }}
            h1 {{
                font-size: 17px !important;
            }}
            .kpi-value {{
                font-size: 19px !important;
            }}
            .stButton > button {{
                min-height: 40px !important;
                padding: 8px 10px !important;
                font-size: 12px !important;
            }}
            .hero-card {{
                padding: 12px 10px !important;
            }}
            .hero-card h1 {{
                font-size: 18px !important;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

def get_status_html(status: str) -> str:
    """Generates accessible status pill HTML matching V9/V12 states."""
    stat_upper = str(status).upper()
    return f'<span class="status-badge {stat_upper}">{status}</span>'
