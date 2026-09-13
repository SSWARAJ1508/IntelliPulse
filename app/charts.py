import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import pandas as pd

def get_chart_layout_updates(theme: str = "dark"):
    """Consistent Plotly styling matching the calm enterprise Design System."""
    is_dark = (theme != "light")
    font_color = '#94A3B8' if is_dark else '#64748B'
    
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=font_color, family='Inter, sans-serif', size=11),
        margin=dict(l=10, r=10, t=10, b=10),
        autosize=True
    )

def plot_gauge(value, title=None, theme: str = "dark"):
    """
    Plot an enterprise health gauge with calibrated semantic colors.
    Strictly contained within card (height: 170px, no overflow).
    """
    is_dark = (theme != "light")
    num_color = '#F8FAFC' if is_dark else '#0F172A'
    track_bg = 'rgba(148, 163, 184, 0.1)' if is_dark else 'rgba(15, 23, 42, 0.06)'
    tick_color = 'rgba(148, 163, 184, 0.2)' if is_dark else 'rgba(15, 23, 42, 0.15)'
    tick_font = '#94A3B8' if is_dark else '#64748B'

    if value is None or (isinstance(value, (int, float)) and np.isnan(value)):
        val_display = 0
        num_str = "N/A"
        bar_color = "rgba(148, 163, 184, 0.25)"
    else:
        val_display = float(value)
        num_str = f"{val_display:.1f}" if val_display != int(val_display) else f"{int(val_display)}"
        
        # Exact Semantic Colors (exclusively for health states)
        if val_display >= 90:
            bar_color = "#16A34A"  # HEALTHY (Green)
        elif val_display >= 75:
            bar_color = "#D97706"  # MONITOR (Amber)
        elif val_display >= 50:
            bar_color = "#EA580C"  # INVESTIGATE (Orange)
        else:
            bar_color = "#DC2626"  # CRITICAL (Red)

    indicator_dict = {
        "mode": "gauge+number",
        "value": val_display,
        "number": {
            'font': {'color': num_color, 'size': 28, 'family': 'Inter'},
            'valueformat': '.1f' if num_str != "N/A" else ''
        },
        "domain": {'x': [0, 1], 'y': [0, 1]},
        "gauge": {
            'axis': {
                'range': [0, 100], 
                'tickwidth': 1, 
                'tickcolor': tick_color, 
                'tickfont': {'color': tick_font, 'size': 9},
                'nticks': 6
            },
            'bar': {'color': bar_color, 'thickness': 0.25},
            'bgcolor': track_bg,
            'borderwidth': 0,
            'steps': [
                {'range': [0, 100], 'color': track_bg}
            ],
            'threshold': {
                'line': {'color': bar_color, 'width': 2},
                'thickness': 0.75,
                'value': val_display
            }
        }
    }
    
    if title:
        indicator_dict["title"] = {'text': title, 'font': {'color': tick_font, 'size': 11.5, 'family': 'Inter'}}
        
    fig = go.Figure(go.Indicator(**indicator_dict))
    layout = get_chart_layout_updates(theme)
    layout["height"] = 170
    fig.update_layout(**layout)
    return fig

def plot_bar(df, x_col, y_col, title=None, color_col=None, theme: str = "dark"):
    """Refined bar chart for drift distribution magnitudes."""
    if df.empty:
        return go.Figure()
        
    is_dark = (theme != "light")
    title_color = '#CBD5E1' if is_dark else '#475569'
    grid_color = 'rgba(148, 163, 184, 0.08)' if is_dark else 'rgba(15, 23, 42, 0.06)'
    line_color = '#334155' if is_dark else '#E2E8F0'
    primary_blue = '#3B82F6'
    
    color_map = {
        1: '#DC2626', 0: primary_blue,
        True: '#DC2626', False: primary_blue,
        "Drifted": '#DC2626', "Stable": primary_blue
    }
    
    fig = px.bar(
        df, x=x_col, y=y_col, title=title, 
        color=color_col,
        color_discrete_map=color_map if color_col else None
    )
    
    if not color_col:
        fig.update_traces(marker_color=primary_blue)
        
    layout = get_chart_layout_updates(theme)
    layout.update(
        title_font=dict(color=title_color, size=12.5),
        xaxis=dict(showgrid=False, linecolor=line_color, tickfont=dict(size=10), title=""),
        yaxis=dict(showgrid=True, gridcolor=grid_color, linecolor=line_color, tickfont=dict(size=10), title=""),
        height=250,
        showlegend=False
    )
    fig.update_layout(**layout)
    return fig

def plot_confusion_matrix(cm_data, title=None, theme: str = "dark"):
    """Clean heatmap for confusion matrix matching enterprise palette."""
    is_dark = (theme != "light")
    title_color = '#CBD5E1' if is_dark else '#475569'
    
    cm = None
    if isinstance(cm_data, dict):
        if 'confusion_matrix' in cm_data and isinstance(cm_data['confusion_matrix'], (list, np.ndarray)):
            cm = np.array(cm_data['confusion_matrix'])
        elif 'matrix' in cm_data:
            val = cm_data['matrix']
            if isinstance(val, dict) and 'confusion_matrix' in val:
                cm = np.array(val['confusion_matrix'])
            elif isinstance(val, (list, np.ndarray)):
                cm = np.array(val)
        elif 'tp' in cm_data and 'tn' in cm_data and cm_data['tp'] is not None and cm_data['tn'] is not None:
            cm = np.array([[int(cm_data.get('tn', 0)), int(cm_data.get('fp', 0))],
                           [int(cm_data.get('fn', 0)), int(cm_data.get('tp', 0))]])
    elif isinstance(cm_data, (list, np.ndarray)):
        cm = np.array(cm_data)

    if cm is None:
        return go.Figure()

    try:
        cm = cm.reshape(2, 2).astype(int)
    except Exception:
        return go.Figure()

    # Labels conforming to enterprise specification
    x_labels = ["Predicted Negative", "Predicted Positive"]
    y_labels = ["Actual Negative", "Actual Positive"]

    # Explicit cell annotations: TN, FP, FN, TP with high readability
    tn_val, fp_val = int(cm[0, 0]), int(cm[0, 1])
    fn_val, tp_val = int(cm[1, 0]), int(cm[1, 1])

    annotations_text = [
        [f"TN: {tn_val:,}", f"FP: {fp_val:,}"],
        [f"FN: {fn_val:,}", f"TP: {tp_val:,}"]
    ]

    plot_bg = "#0F172A" if is_dark else "#FFFFFF"
    text_color = "#F8FAFC" if is_dark else "#0F172A"

    # Restrained monochromatic blue scale (NO neon cyan)
    colorscale = [
        [0.0, "#172235" if is_dark else "#F1F5F9"],
        [0.5, "#1E3A8A" if is_dark else "#93C5FD"],
        [1.0, "#2563EB" if is_dark else "#2563EB"]
    ]

    fig = go.Figure(data=go.Heatmap(
        z=cm,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        text=annotations_text,
        texttemplate="%{text}",
        textfont={"size": 13.5, "family": "Inter", "color": text_color},
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br><b>%{x}</b><br>Count: %{z:,}<extra></extra>",
        showscale=False
    ))

    layout = get_chart_layout_updates(theme)
    layout.update(
        title_font=dict(color=title_color, size=12.5),
        paper_bgcolor=plot_bg,
        plot_bgcolor=plot_bg,
        height=240,
        margin=dict(l=40, r=25, t=25, b=35),
        xaxis=dict(
            tickfont=dict(size=11, color=text_color, family="Inter"),
            side="bottom",
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            tickfont=dict(size=11, color=text_color, family="Inter"),
            showgrid=False,
            zeroline=False,
            autorange="reversed"
        )
    )
    fig.update_layout(**layout)
    return fig

def plot_performance_trend(df, metric_col="f1", theme: str = "dark"):
    """Area fill line chart for performance progression."""
    if df.empty or metric_col not in df.columns:
        return go.Figure()

    is_dark = (theme != "light")
    title_color = '#CBD5E1' if is_dark else '#475569'
    grid_color = 'rgba(148, 163, 184, 0.08)' if is_dark else 'rgba(15, 23, 42, 0.06)'
    line_color = '#2563EB'
    fill_color = 'rgba(37, 99, 235, 0.08)'

    fig = go.Figure()
    x_axis = df['batch_id'] if 'batch_id' in df.columns else df.index
    
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=df[metric_col],
        mode='lines+markers',
        line=dict(color=line_color, width=2),
        marker=dict(size=5, color=line_color, line=dict(width=1, color='#FFFFFF')),
        fill='tozeroy',
        fillcolor=fill_color,
        name=metric_col.upper()
    ))

    layout = get_chart_layout_updates(theme)
    layout.update(
        height=230,
        title_font=dict(color=title_color, size=12.5),
        xaxis=dict(showgrid=False, tickfont=dict(size=10), title=""),
        yaxis=dict(showgrid=True, gridcolor=grid_color, range=[0, 1.05], tickfont=dict(size=10), title="")
    )
    fig.update_layout(**layout)
    return fig
