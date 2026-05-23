"""
app.py  ·  DataNova — AI BI Platform
Run:  streamlit run app.py
"""

import os, io, time, tempfile, uuid, re, requests
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import inspect
from fpdf import FPDF

from agent import run_generation, run_execution, generate_sample_questions, generate_executive_summary, auto_generate_dashboard, analyze_data_insights, edit_dashboard, explain_chart, generate_recommendations, generate_followup_questions, build_generation_graph, build_execution_graph
from setup_db import create_database, DB_PATH, register_upload, register_query_log, get_query_log
from database import DatabaseConnector

# ── Page config ──
st.set_page_config(page_title="DataNova", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ── Theme state ──
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# ── CSS Variables + Theming ──
LIGHT_VARS = {
    "bg": "linear-gradient(135deg, #f0f4ff 0%, #e8eeff 50%, #f5f0ff 100%)",
    "bg2": "#ffffff",
    "card": "rgba(255,255,255,0.95)",
    "card-border": "rgba(99,102,241,0.2)",
    "sidebar": "rgba(255,255,255,0.98)",
    "text": "#0f172a",
    "text2": "#475569",
    "accent": "#4f46e5",
    "accent2": "#7c3aed",
    "hover": "rgba(79,70,229,0.1)",
    "shadow": "rgba(79,70,229,0.12)",
    "input-bg": "#ffffff",
    "input-border": "rgba(79,70,229,0.25)",
    "glow": "rgba(79,70,229,0.2)",
}
DARK_VARS = {
    "bg": "linear-gradient(135deg, #0f172a 0%, #111827 40%, #1e1b4b 100%)",
    "bg2": "#1e293b",
    "card": "rgba(255,255,255,0.08)",
    "card-border": "rgba(255,255,255,0.12)",
    "sidebar": "rgba(15,23,42,0.95)",
    "text": "#ffffff",
    "text2": "#cbd5e1",
    "accent": "#818cf8",
    "accent2": "#a78bfa",
    "hover": "rgba(129,140,248,0.15)",
    "shadow": "rgba(0,0,0,0.5)",
    "input-bg": "rgba(255,255,255,0.10)",
    "input-border": "rgba(255,255,255,0.20)",
    "glow": "rgba(139,92,246,0.40)",
}

def get_theme_css(theme):
    v = DARK_VARS if theme == "dark" else LIGHT_VARS
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Syne:wght@400;600;800&family=Space+Mono:wght@400;700&display=swap');

    :root {{
        --bg: {v["bg"]};
        --bg2: {v["bg2"]};
        --card: {v["card"]};
        --card-border: {v["card-border"]};
        --sidebar: {v["sidebar"]};
        --text: {v["text"]};
        --text2: {v["text2"]};
        --accent: {v["accent"]};
        --accent2: {v["accent2"]};
        --hover: {v["hover"]};
        --shadow: {v["shadow"]};
        --input-bg: {v["input-bg"]};
        --input-border: {v["input-border"]};
        --glow: {v["glow"]};
    }}

    * {{ box-sizing: border-box; }}

    html, body, .stApp {{
        background: var(--bg) !important;
        color: var(--text);
    }}
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--text);
    }}

    /* ── Soft grid background ── */
    body::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image:
            linear-gradient(rgba(129,140,248,0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(129,140,248,0.06) 1px, transparent 1px);
        background-size: 40px 40px;
        pointer-events: none;
        z-index: 0;
    }}
    .stApp > div {{ position: relative; z-index: 1; }}

    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: var(--accent); border-radius: 3px; }}

    /* ── Glass card base ── */
    .glass-card {{
        background: var(--card);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid var(--card-border);
        border-radius: 24px;
        box-shadow: 0 8px 32px var(--shadow);
        padding: 1.25rem;
        transition: all 0.3s ease;
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background: rgba(15,23,42,0.82) !important;
        border-right: 1px solid var(--card-border) !important;
        backdrop-filter: blur(20px) !important;
        padding: 0 !important;
        gap: 0 !important;
        min-width: 240px !important;
        max-width: 240px !important;
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        overflow-y: auto !important;
        max-height: 100vh !important;
        padding: 0.75rem !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: var(--text) !important;
    }}
    section[data-testid="stSidebar"] button:not([kind="primary"]) {{
        background: var(--card) !important;
        border: 1px solid var(--card-border) !important;
        color: var(--text) !important;
        border-radius: 12px !important;
        padding: 0.35rem 0.75rem !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }}
    section[data-testid="stSidebar"] input[type="text"] {{
        background: var(--input-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 12px !important;
        padding: 0.5rem 0.75rem !important;
        margin-bottom: 0.25rem !important;
    }}
    section[data-testid="stSidebar"] input[type="text"]::placeholder {{
        color: var(--text2) !important;
    }}
    section[data-testid="stSidebar"] textarea {{
        background: var(--input-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 12px !important;
    }}
    section[data-testid="stSidebar"] button:not([kind="primary"]):hover {{
        background: var(--hover) !important;
        border-color: var(--accent) !important;
    }}
    section[data-testid="stSidebar"] .st-emotion-cache-1wivap2,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }}
    section[data-testid="stSidebar"] .section-title {{
        margin-bottom: 0.5rem !important;
        margin-top: 0.75rem !important;
    }}
    section[data-testid="stSidebar"] .section-title:first-child {{
        margin-top: 0 !important;
    }}
    section[data-testid="stSidebar"] hr {{
        margin: 0.6rem 0 !important;
    }}

    /* ── Sidebar collapse / re-open toggle ── */
    button[data-testid="baseButton-header"] {{
        font-size: 1.3rem !important;
        background: var(--card) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 12px !important;
        padding: 0.2rem 0.5rem !important;
        box-shadow: 0 2px 8px var(--shadow) !important;
        transition: all 0.2s !important;
        opacity: 1 !important;
    }}
    button[data-testid="baseButton-header"]:hover {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 16px var(--glow) !important;
    }}
    /* ── Top Bar wrappers ── */
    .topbar-hamburger, .topbar-theme {{
        background: var(--card);
        backdrop-filter: blur(24px) saturate(1.4);
        -webkit-backdrop-filter: blur(24px) saturate(1.4);
        border: 1px solid var(--card-border);
        border-radius: 20px;
        padding: 0.2rem 0.3rem;
        box-shadow: 0 4px 24px var(--shadow);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: box-shadow 0.3s ease;
    }}
    .topbar-hamburger:hover, .topbar-theme:hover {{
        box-shadow: 0 6px 32px var(--shadow), 0 0 0 1px rgba(129,140,248,0.15);
    }}
    .topbar-hamburger button, .topbar-theme button {{
        font-size: 1.05rem !important;
        padding: 0.15rem 0.4rem !important;
        border-radius: 14px !important;
        border: 1px solid var(--card-border) !important;
        background: var(--input-bg) !important;
        min-width: unset !important;
        width: auto !important;
        box-shadow: none !important;
        line-height: 1.3 !important;
        color: var(--text) !important;
        transition: all 0.2s !important;
    }}
    .topbar-hamburger button:hover, .topbar-theme button:hover {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 16px var(--glow) !important;
    }}
    .topbar-brand {{
        padding: 0.3rem 0 0.3rem 0.5rem;
        overflow: visible;
        min-width: fit-content;
    }}
    .stSidebarCollapsedButton {{
        font-size: 1.5rem !important;
        background: var(--card) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 12px !important;
        padding: 0.4rem 0.65rem !important;
        margin: 0.5rem !important;
        box-shadow: 0 4px 16px var(--shadow) !important;
        opacity: 1 !important;
        transition: all 0.2s !important;
    }}
    .stSidebarCollapsedButton:hover {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 20px var(--glow) !important;
        transform: scale(1.05);
    }}

    /* ── Top Bar ── */
    div[data-testid="column"]:has(> div[style*="Syne"]) {{
        padding: 0.2rem 0 0.2rem 0.5rem !important;
    }}
    div[data-testid="column"]:first-child button,
    div[data-testid="column"]:last-child button {{
        font-size: 1.05rem !important;
        padding: 0.15rem 0.4rem !important;
        border-radius: 14px !important;
        border: 1px solid var(--card-border) !important;
        background: var(--input-bg) !important;
        min-width: unset !important;
        width: auto !important;
        box-shadow: none !important;
        line-height: 1.3 !important;
    }}
    @keyframes gradient-shift {{
        0% {{ background-position: 0% center; }}
        50% {{ background-position: 100% center; }}
        100% {{ background-position: 0% center; }}
    }}

    /* ── Glass KPI Cards ── */
    .kpi-card {{
        background: linear-gradient(135deg, rgba(129,140,248,0.12), rgba(167,139,250,0.06));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--card-border);
        border-radius: 22px;
        padding: 1.25rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    .kpi-card:hover {{
        transform: translateY(-4px);
        border-color: var(--accent);
        box-shadow: 0 12px 40px var(--shadow);
    }}
    .kpi-card .kpi-value {{
        transition: all 0.3s ease;
    }}
    .kpi-card:hover .kpi-value {{
        transform: scale(1.02);
    }}
    /* Chart card micro-animation */
    .chart-card {{
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    .chart-card:hover {{
        transform: translateY(-2px);
    }}
    /* Executive Summary typography */
    .exec-summary {{
        line-height: 1.8 !important;
        font-size: 0.92rem !important;
        color: var(--text2) !important;
    }}
    .exec-summary strong {{
        color: var(--text) !important;
    }}
    .exec-summary .highlight {{
        color: var(--accent) !important;
        font-weight: 600;
    }}
    .kpi-card::after {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent), var(--accent2), #e879f9);
        opacity: 0;
        transition: opacity 0.3s;
    }}
    .kpi-card:hover::after {{ opacity: 1; }}
    .kpi-label {{
        font-size: 0.7rem;
        font-weight: 600;
        color: var(--text2);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
        opacity: 0.8;
    }}
    .kpi-value {{
        font-family: 'Inter', sans-serif;
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text);
        line-height: 1.15;
    }}
    .kpi-trend {{ font-size: 0.75rem; font-weight: 600; margin-top: 0.35rem; }}
    .kpi-trend.up {{ color: #22c55e; }}
    .kpi-trend.down {{ color: #ef4444; }}

    /* ── Chart containers ── */
    .chart-card {{
        background: var(--card);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--card-border);
        border-radius: 20px;
        padding: 0.65rem 0.85rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 4px 16px var(--shadow);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .chart-card:hover {{
        border-color: var(--accent);
        box-shadow: 0 8px 32px var(--shadow);
    }}
    .chart-title {{
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 0.4rem;
        opacity: 0.9;
    }}

    /* ── Chat Input (ChatGPT-style) ── */
    div[data-testid="stChatInput"] textarea {{
        background: var(--input-bg) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 18px !important;
        color: var(--text) !important;
        font-size: 0.95rem !important;
        padding: 14px 18px !important;
        transition: all 0.25s ease !important;
        backdrop-filter: blur(8px) !important;
    }}
    div[data-testid="stChatInput"] textarea:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--hover), 0 0 20px var(--glow) !important;
    }}
    div[data-testid="stChatInput"] textarea::placeholder {{
        color: var(--text2) !important;
        opacity: 0.6;
    }}

    /* ── Chat messages ── */
    div[data-testid="stChatMessage"] {{
        background: var(--card) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 18px !important;
        padding: 0.85rem 1.1rem !important;
        margin-bottom: 0.6rem !important;
        color: var(--text) !important;
        box-shadow: 0 2px 8px var(--shadow) !important;
        transition: all 0.2s !important;
    }}
    div[data-testid="stChatMessage"]:hover {{
        border-color: var(--accent) !important;
    }}

    /* ── SQL / Code box ── */
    .sql-box {{
        background: var(--input-bg);
        backdrop-filter: blur(8px);
        border: 1px solid var(--card-border);
        border-left: 3px solid var(--accent);
        border-radius: 12px;
        padding: 0.7rem 0.9rem;
        font-family: 'Space Mono', monospace;
        font-size: 0.78rem;
        color: var(--text);
        white-space: pre-wrap;
        word-break: break-word;
        overflow-x: auto;
    }}

    /* ── Metrics ── */
    div[data-testid="stMetric"] {{
        background: var(--card) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 18px !important;
        padding: 0.9rem !important;
        transition: all 0.2s;
    }}
    div[data-testid="stMetric"]:hover {{
        border-color: var(--accent) !important;
        box-shadow: 0 4px 16px var(--shadow) !important;
    }}
    div[data-testid="stMetricValue"] {{
        color: var(--accent) !important;
        font-weight: 800 !important;
        font-size: 1.5rem !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: var(--text2) !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}

    /* ── Buttons ── */
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.5; transform: scale(1.2); }}
    }}
    button {{
        border-radius: 14px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    button[kind="primary"] {{
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
    }}
    button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px var(--glow) !important;
    }}
    button[kind="primary"]:active {{
        transform: translateY(0px) !important;
    }}

    /* ── Tags ── */
    .tag {{
        display: inline-block;
        background: linear-gradient(135deg, rgba(129,140,248,0.15), rgba(167,139,250,0.1));
        border: 1px solid var(--accent);
        color: var(--accent);
        border-radius: 20px;
        font-size: 0.62rem;
        padding: 2px 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    /* ── Status boxes ── */
    .error-box, .success-box, .info-box {{
        border-radius: 12px;
        padding: 0.65rem 0.9rem;
        font-size: 0.82rem;
        border-left: 3px solid;
        backdrop-filter: blur(8px);
    }}
    .error-box {{ background: rgba(239,68,68,0.12); border-color: #ef4444; color: #fca5a5; }}
    .success-box {{ background: rgba(34,197,94,0.12); border-color: #22c55e; color: #86efac; }}
    .info-box {{ background: rgba(59,130,246,0.12); border-color: #3b82f6; color: #93c5fd; }}

    /* ── Divider ── */
    hr {{
        border: none !important;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--card-border), transparent) !important;
        margin: 0.75rem 0 !important;
    }}

    /* ── Data quality panel ── */
    .dq-panel {{
        background: var(--card);
        backdrop-filter: blur(12px);
        border: 1px solid var(--card-border);
        border-radius: 18px;
        padding: 0.9rem;
        font-size: 0.78rem;
    }}
    .dq-row {{
        display: flex; justify-content: space-between;
        padding: 0.3rem 0;
        border-bottom: 1px solid var(--card-border);
    }}
    .dq-row:last-child {{ border-bottom: none; }}
    .dq-label {{ color: var(--text2); }}
    .dq-value {{ font-weight: 700; color: var(--text); }}

    /* ── AI thinking ── */
    .ai-thinking {{
        padding: 0.5rem 0;
    }}
    .ai-step {{
        padding: 0.35rem 0;
        font-size: 0.8rem;
        color: var(--text2);
        display: flex; align-items: center; gap: 0.55rem;
        opacity: 0.7;
    }}
    .ai-step.active {{
        color: var(--accent);
        font-weight: 600;
        opacity: 1;
    }}
    .ai-step.done {{
        color: #22c55e;
        opacity: 1;
    }}
    .ai-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--text2);
        display: inline-block;
        flex-shrink: 0;
    }}
    .ai-step.active .ai-dot {{
        background: var(--accent);
        animation: pulse-dot 1s ease infinite;
        box-shadow: 0 0 8px var(--accent);
    }}
    .ai-step.done .ai-dot {{ background: #22c55e; }}
    @keyframes pulse-dot {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.6; transform: scale(1.5); }}
    }}

    /* ── Empty state ── */
    .empty-state {{
        border: 1px dashed var(--card-border);
        border-radius: 24px;
        padding: 3rem 1.5rem;
        text-align: center;
        background: var(--card);
        backdrop-filter: blur(8px);
    }}

    /* ── Typography ── */
    h1, h2, h3, h4 {{
        font-family: 'Inter', sans-serif !important;
        letter-spacing: -0.02em !important;
    }}
    h1 {{ font-size: 2rem !important; font-weight: 800 !important; }}
    h2 {{ font-size: 1.5rem !important; font-weight: 700 !important; }}
    h3 {{ font-size: 1.2rem !important; font-weight: 700 !important; }}
    h4 {{ font-size: 1rem !important; font-weight: 600 !important; }}
    p, li, .stMarkdown > div > p {{
        color: var(--text2);
        line-height: 1.6;
    }}

    /* ── Tabs styled as premium pills ── */
    button[data-baseweb="tab"] {{
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: var(--text2) !important;
        background: transparent !important;
        border-radius: 14px !important;
        padding: 0.4rem 1rem !important;
        margin: 0 0.15rem !important;
        border: none !important;
        transition: all 0.25s ease !important;
    }}
    button[data-baseweb="tab"]:hover {{
        background: var(--hover) !important;
        color: var(--text) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
        color: #fff !important;
        box-shadow: 0 4px 16px var(--glow) !important;
    }}
    div[data-baseweb="tab-list"] {{
        gap: 0.25rem !important;
        background: var(--card) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 20px !important;
        padding: 0.3rem !important;
        margin-bottom: 0.75rem !important;
        box-shadow: 0 4px 24px var(--shadow) !important;
    }}
    div[data-baseweb="tab-highlight"] {{
        display: none !important;
    }}

    /* ── Force theme-aware backgrounds on all containers ── */
    .stApp, .stApp > div, div[data-testid="stAppViewContainer"],
    div[data-testid="stHeader"], div[data-testid="stToolbar"],
    section[data-testid="stSidebar"] > div:first-child,
    div[data-testid="stMainBlockContainer"] {{
        background: var(--bg) !important;
    }}
    div[data-testid="stVerticalBlock"] > div,
    div[data-testid="stHorizontalBlock"],
    div[data-testid="column"] > div {{
        background: transparent !important;
    }}

    /* ── Compact spacing ── */
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    .main > div {{ padding-top: 0 !important; padding-bottom: 0 !important; }}
    div.block-container {{
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
        max-width: 100% !important;
    }}
    .row-widget.stTabs {{ margin-bottom: 0 !important; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.25rem; margin-bottom: 0.15rem; }}
    .stTabs [data-baseweb="tab"] {{ font-size: 0.8rem; padding: 0.2rem 0.5rem; }}
    div[data-testid="stVerticalBlock"] > div {{ gap: 0.35rem !important; }}

    /* ── Sidebar narrower ── */
    section[data-testid="stSidebar"] {{
        min-width: 220px !important;
        max-width: 260px !important;
    }}

    /* ── File uploader glass ── */
    section[data-testid="stFileUploader"] {{
        background: var(--card) !important;
        border: 1px dashed var(--card-border) !important;
        border-radius: 20px !important;
        backdrop-filter: blur(8px) !important;
        padding: 0.5rem !important;
        transition: all 0.25s ease !important;
    }}
    section[data-testid="stFileUploader"]:hover {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 20px var(--glow) !important;
    }}
    section[data-testid="stFileUploader"] button {{
        background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 12px !important;
    }}

    /* ── DataFrame ── */
    div[data-testid="stDataFrame"] {{
        border: 1px solid var(--card-border) !important;
        border-radius: 14px !important;
        overflow: hidden !important;
    }}

    /* ── Expander ── */
    details {{
        border: 1px solid var(--card-border) !important;
        border-radius: 14px !important;
        background: var(--card) !important;
        backdrop-filter: blur(8px) !important;
        padding: 0.2rem 0.6rem !important;
        margin-bottom: 0.3rem !important;
    }}
    details summary {{
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        color: var(--text) !important;
        padding: 0.3rem 0 !important;
    }}

    /* ── Custom tab buttons (compact pills) ── */
    div[data-testid="column"] button[kind="primary"] {{
        background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        padding: 0.25rem 0.5rem !important;
        box-shadow: 0 4px 16px var(--glow) !important;
        min-height: 0 !important;
        height: auto !important;
    }}
    div[data-testid="column"] button[kind="secondary"] {{
        background: var(--card) !important;
        color: var(--text2) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 14px !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        padding: 0.25rem 0.5rem !important;
        backdrop-filter: blur(8px) !important;
        min-height: 0 !important;
        height: auto !important;
    }}
    div[data-testid="column"] button[kind="secondary"]:hover {{
        border-color: var(--accent) !important;
        color: var(--text) !important;
    }}

    /* ── Feature cards hover ── */
    .feature-card {{
        text-align: center;
        padding: 1.2rem 0.5rem;
        background: var(--card);
        border: 1px solid var(--card-border);
        border-radius: 18px;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: default;
    }}
    .feature-card:hover {{
        transform: translateY(-6px);
        border-color: var(--accent);
        box-shadow: 0 12px 30px var(--glow);
    }}

    /* ── Text inputs glass ── */
    input[type="text"], input[type="url"], input[type="search"], textarea:not([data-testid="stChatInput"] textarea) {{
        background: var(--input-bg) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 14px !important;
        color: var(--text) !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.2s !important;
    }}
    input:focus {{ border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--hover) !important; }}

    /* ── Select boxes glass ── */
    div[data-baseweb="select"] > div {{
        background: var(--input-bg) !important;
        border: 1px solid var(--input-border) !important;
        border-radius: 14px !important;
        backdrop-filter: blur(8px) !important;
    }}

    /* ── Section title hierarchy ── */
    .section-title {{
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.25rem !important;
    }}
    .section-sub {{
        font-size: 0.78rem !important;
        color: var(--text2) !important;
        opacity: 0.7 !important;
        margin-bottom: 0.5rem !important;
    }}
    </style>
    """

# ── DB bootstrap ──
if not os.path.exists(DB_PATH):
    with st.spinner("Initializing database..."):
        create_database()

# ── Session State ──
defaults = {
    "messages": [],
    "pinned_charts": [],
    "auto_dashboards": {},
    "selected_dashboard": None,
    "cached_questions": {},
    "sidebar_open": True,
    "selected_tab": "💬 Chat",
    "dash_edit_messages": [],
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ── Inject theme CSS ──
st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

# ── Top Bar ──
theme_icon = "🌙" if st.session_state.theme == "light" else "☀️"
top1, top2, top3 = st.columns([1, 8, 1], gap="small")
with top1:
    st.markdown('<div class="topbar-hamburger">', unsafe_allow_html=True)
    if st.button("☰", key="sidebar_toggle_top", help="Toggle sidebar"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with top2:
    st.markdown('<div class="topbar-brand"><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.4rem;background:linear-gradient(90deg,var(--accent),var(--accent2),#e879f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">DataNova</span></div>', unsafe_allow_html=True)
with top3:
    st.markdown('<div class="topbar-theme">', unsafe_allow_html=True)
    if st.button(theme_icon, key="theme_toggle_top", help="Toggle theme"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Sidebar visibility CSS ──
if not st.session_state.sidebar_open:
    st.markdown('''
    <style>
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    .stApp > header + div {
        margin-left: 0 !important;
    }
    </style>
    ''', unsafe_allow_html=True)

# ── Helper functions ──
def auto_chart(df: pd.DataFrame):
    if len(df) < 2 or len(df.columns) < 2:
        return None
    num_cols = [c for c in df.columns if "int" in str(df[c].dtype) or "float" in str(df[c].dtype)]
    cat_cols = [c for c in df.columns if "object" in str(df[c].dtype) or "cate" in str(df[c].dtype)]
    if len(num_cols) >= 1 and len(cat_cols) >= 1:
        return px.bar(df, x=cat_cols[0], y=num_cols[0], color_discrete_sequence=["#818cf8"])
    if len(num_cols) >= 2:
        return px.line(df, x=num_cols[0], y=num_cols[1], color_discrete_sequence=["#818cf8"])
    if len(cat_cols) >= 2:
        c = cat_cols[0]
        if len(df[c].unique()) > 6:
            return px.bar(df, x=c, y=cat_cols[1] if len(cat_cols) > 1 else None, color_discrete_sequence=["#818cf8"])
        return px.pie(df, names=c, color_discrete_sequence=["#818cf8", "#a78bfa", "#e879f9", "#fbbf24", "#34d399"])
    return None

def _apply_chart_layout(fig):
    is_dark = st.session_state.theme == "dark"
    text_color = "#ffffff" if is_dark else "#0f172a"
    text2_color = "#cbd5e1" if is_dark else "#64748b"
    grid_color = "rgba(148,163,184,0.15)" if is_dark else "rgba(99,102,241,0.1)"
    chart_bg = "rgba(15,23,42,0.4)" if is_dark else "rgba(248,250,255,0.6)"
    legend_bg = "rgba(30,41,59,0.8)" if is_dark else "rgba(255,255,255,0.9)"
    hover_bg = "rgba(30,41,59,0.95)" if is_dark else "rgba(255,255,255,0.95)"
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=chart_bg,
        font=dict(family="Inter", size=11, color=text_color),
        margin=dict(l=0, r=0, t=32, b=0),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=hover_bg, font_size=11, font_family="Inter", font_color=text_color),
        showlegend=True,
        legend=dict(
            bgcolor=legend_bg,
            bordercolor="rgba(129,140,248,0.2)",
            borderwidth=1,
            font=dict(color=text2_color)
        ),
        dragmode=False,
    )
    fig.update_xaxes(showgrid=False, color=text2_color, tickfont=dict(color=text2_color))
    fig.update_yaxes(showgrid=True, gridcolor=grid_color, color=text2_color, tickfont=dict(color=text2_color))

def render_dynamic_chart(df: pd.DataFrame, spec, key=None):
    if len(df) < 2 or len(df.columns) < 2:
        return None
    fig = None
    if spec is None:
        fig = auto_chart(df)
    elif hasattr(spec, "to_plotly_json"):
        fig = spec
    elif isinstance(spec, dict) and "type" in spec:
        ct = spec.get("type", "").lower()
        xc, yc = spec.get("x"), spec.get("y")
        try:
            if ct == "pie" and xc:
                if yc and len(df[xc].unique()) > 6:
                    ct, yc, xc = "bar", xc, yc
                else:
                    fig = px.pie(df, names=xc, values=yc if yc else None,
                                 color_discrete_sequence=["#818cf8", "#a78bfa", "#e879f9", "#fbbf24", "#34d399", "#22d3ee"])
            if ct == "bar" and xc and yc:
                fig = px.bar(df, x=xc, y=yc, color_discrete_sequence=["#818cf8", "#a78bfa", "#e879f9"])
            elif ct == "line" and xc and yc:
                fig = px.line(df, x=xc, y=yc, color_discrete_sequence=["#818cf8", "#22d3ee"])
            elif ct == "scatter" and xc and yc:
                fig = px.scatter(df, x=xc, y=yc, color_discrete_sequence=["#818cf8"])
            elif ct == "pie" and xc:
                fig = px.pie(df, names=xc, values=yc if yc else None,
                             color_discrete_sequence=["#818cf8", "#a78bfa", "#e879f9", "#fbbf24", "#34d399", "#22d3ee"])
        except Exception:
            fig = auto_chart(df)
    if fig is None:
        fig = auto_chart(df)
    if fig:
        _apply_chart_layout(fig)
        st.plotly_chart(fig, width='stretch',
                        config={"responsive": True, "displayModeBar": True, "displaylogo": False,
                                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                                "modeBarButtonsToAdd": ["drawrect", "eraseshape"],
                                "staticPlot": False},
                        key=key)
        # ── Drill-down toggle ──
        drill_key = f"drill_{key}" if key else f"drill_{id(df)}"
        if st.button("🔍 Drill down", key=drill_key, help="View raw data behind this chart"):
            with st.container():
                st.dataframe(df, width='stretch', height=200)
        # ── Explain chart ──
        explain_key = f"explain_{key}" if key else f"explain_{id(df)}"
        explain_text = st.session_state.get(explain_key, "")
        if not explain_text:
            if st.button("💡 Explain this chart", key=f"btn_{explain_key}", help="Plain-English explanation"):
                with st.spinner(""):
                    _ct = spec.get("type", "chart") if isinstance(spec, dict) else "chart"
                    _xc = spec.get("x") if isinstance(spec, dict) else None
                    _yc = spec.get("y") if isinstance(spec, dict) else None
                    st.session_state[explain_key] = explain_chart(df, _ct, _xc, _yc)
                st.rerun()
        else:
            st.markdown(f'<div style="padding:0.5rem 0.7rem;margin-top:0.3rem;background:var(--card);border:1px solid var(--card-border);border-radius:12px;font-size:0.82rem;line-height:1.6;color:var(--text2);">💡 <b>What This Means</b><br>{explain_text}</div>', unsafe_allow_html=True)
            if st.button("✕", key=f"close_{explain_key}", help="Dismiss"):
                st.session_state.pop(explain_key, None)
                st.rerun()
    return fig

def sanitize_table_name(name: str) -> str:
    name = os.path.splitext(name)[0]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_').lower()
    if not name or name.upper() in {
        "SELECT","FROM","WHERE","GROUP","ORDER","BY","LIMIT",
        "INSERT","UPDATE","DELETE","DROP","ALTER","CREATE",
        "TABLE","INTO","VALUES","SET","AND","OR","NOT","IN",
        "LIKE","BETWEEN","IS","NULL","AS","ON","JOIN","LEFT",
        "RIGHT","INNER","OUTER","FULL","UNION","ALL","DISTINCT",
        "CASE","WHEN","THEN","ELSE","END","EXISTS","HAVING",
        "COUNT","SUM","AVG","MIN","MAX","ASC","DESC",
    }:
        name = "uploaded_data"
    return name

def _apply_filter(sql: str, filt: tuple) -> str:
    if not filt:
        return sql
    col, _ = filt
    insert_pos = len(sql)
    for kw in ["GROUP BY", "ORDER BY", "LIMIT"]:
        pos = sql.upper().find(kw)
        if pos != -1 and pos < insert_pos:
            insert_pos = pos
    if " WHERE " not in sql.upper():
        return sql[:insert_pos] + f"WHERE [{col}] = :fv " + sql[insert_pos:]
    if ":fv" not in sql:
        return sql.replace("WHERE ", f"WHERE [{col}] = :fv AND ")
    return sql

def render_kpi_card(label, value, trend=None, icon=None, fmt="number"):
    if value is not None:
        if fmt == "currency": display = f"${value:,.2f}"
        elif fmt == "percent": display = f"{value:.1f}%"
        elif fmt == "integer": display = f"{int(value):,}"
        else: display = f"{value:,.2f}"
    else:
        display = "—"
    trend_html = ""
    if trend is not None:
        arrow = "↑" if trend >= 0 else "↓"
        cls = "up" if trend >= 0 else "down"
        trend_html = f'<div class="kpi-trend {cls}">{arrow} {abs(trend):.1f}%</div>'
    icon_html = f'<span style="font-size:1.1rem;margin-right:0.4rem;">{icon}</span>' if icon else ""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{icon_html}{label}</div>
        <div class="kpi-value">{display}</div>
        {trend_html}
    </div>
    """, unsafe_allow_html=True)

def render_data_quality_panel(df: pd.DataFrame):
    if df is None or len(df) == 0:
        return
    nulls = df.isnull().sum().sum()
    total = df.size
    dupes = df.duplicated().sum()
    quality = round((1 - (nulls + dupes) / max(total, 1)) * 100)
    st.markdown('<div class="dq-panel">'
        f'<div style="font-weight:700;font-size:0.85rem;margin-bottom:0.5rem;">📋 Data Quality</div>'
        f'<div class="dq-row"><span class="dq-label">Quality Score</span><span class="dq-value">{quality}%</span></div>'
        f'<div class="dq-row"><span class="dq-label">Rows</span><span class="dq-value">{len(df):,}</span></div>'
        f'<div class="dq-row"><span class="dq-label">Columns</span><span class="dq-value">{len(df.columns)}</span></div>'
        f'<div class="dq-row"><span class="dq-label">Missing Values</span><span class="dq-value">{nulls}</span></div>'
        f'<div class="dq-row"><span class="dq-label">Duplicates</span><span class="dq-value">{dupes}</span></div>'
        '</div>', unsafe_allow_html=True)

def render_insight_cards(insights):
    for ins in insights:
        if isinstance(ins, dict):
            icon = ins.get("icon", "💡")
            label = ins.get("label", "")
            detail = ins.get("detail", "")
            st.markdown(f'''<div style="display:flex;gap:0.5rem;align-items:flex-start;padding:0.3rem 0;border-bottom:1px solid var(--card-border);">
                <span style="font-size:1.1rem;flex-shrink:0;">{icon}</span>
                <div><div style="font-weight:600;font-size:0.78rem;">{label}</div><div style="font-size:0.68rem;color:var(--text2);">{detail}</div></div>
            </div>''', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.78rem;padding:0.2rem 0;">{ins}</div>', unsafe_allow_html=True)

def ai_thinking_placeholder(ph, steps):
    """Animated AI thinking steps in a placeholder."""
    html = '<div style="padding:0.5rem 0;">'
    for s in steps:
        html += f'<div class="ai-step active"><span class="ai-dot"></span>{s}</div>'
    html += '</div>'
    ph.markdown(html, unsafe_allow_html=True)

def db_conn() -> DatabaseConnector:
    return DatabaseConnector(f"sqlite:///{DB_PATH}")
def db_engine():
    return db_conn().engine

@st.cache_resource
def get_cached_connector(url):
    return DatabaseConnector(url)

@st.cache_data(ttl=30)
def get_cached_tables(conn_url):
    c = get_cached_connector(conn_url)
    return c.get_tables() if c.test_connection() else []

@st.cache_data(ttl=30)
def get_cached_schema(conn_url, table_name):
    c = get_cached_connector(conn_url)
    return c.get_table_schema(table_name) if c.test_connection() else ""

@st.cache_resource
def get_generation_graph():
    return build_generation_graph()

@st.cache_resource
def get_execution_graph():
    return build_execution_graph()

# ── Sidebar ──
with st.sidebar:
    st.markdown('<p class="section-title" style="font-size:0.85rem;">🔌 Connection</p>', unsafe_allow_html=True)
    db_url_input = st.text_input("Database URI", value=f"sqlite:///{DB_PATH}", key="db_url_input", label_visibility="collapsed")
    db_conn_side = get_cached_connector(db_url_input)
    is_connected = db_conn_side.test_connection()
    if is_connected:
        st.markdown('<div class="success-box">✓ Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="error-box">✗ Connection failed</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title" style="font-size:0.85rem;">📂 Tables</p>', unsafe_allow_html=True)
    if is_connected:
        tables = get_cached_tables(db_url_input)
        user_tables = [t for t in tables if not t.startswith("_")]
        if user_tables:
            for t in user_tables:
                schema = get_cached_schema(db_url_input, t)
                col_count = schema.count(",") + 1
                try:
                    row_count = get_cached_connector(db_url_input).execute_query(f"SELECT COUNT(*) FROM \"{t}\"").iloc[0, 0]
                except Exception:
                    row_count = "?"
                st.markdown(f'''<div style="background:var(--card);border:1px solid var(--card-border);border-radius:12px;padding:0.4rem 0.7rem;margin-bottom:0.25rem;">
                    <div style="font-weight:600;font-size:0.82rem;">{t}</div>
                    <div style="font-size:0.68rem;color:var(--text2);">{col_count} columns · {row_count} rows</div>
                </div>''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-state" style="padding:1rem;"><p style="color:var(--text2);font-size:0.8rem;"> No tables yet — upload data in the <b>Data</b> tab</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state" style="padding:0.75rem;"><p style="color:var(--text2);font-size:0.8rem;"> Not connected</p></div>', unsafe_allow_html=True)

    st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
    with st.expander("📖 Data Dictionary", expanded=False):
        data_dictionary = st.text_area("Business rules", "", height=100,
            placeholder="Revenue = price * quantity\nActive users = logged in within 30 days")

    if is_connected:
        tables = get_cached_tables(db_url_input)
        user_tables = [t for t in tables if not t.startswith("_")]
        if user_tables:
            st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
            st.markdown('<p class="section-title" style="font-size:0.85rem;">💡 Questions</p>', unsafe_allow_html=True)
            if db_url_input not in st.session_state["cached_questions"]:
                with st.spinner("Generating..."):
                    try:
                        qs = generate_sample_questions(db_url_input)
                    except Exception as e:
                        st.warning(f"Could not generate questions: {e}")
                        qs = ["Show me the data", "What are the top trends?", "Summarize insights"]
                    st.session_state["cached_questions"][db_url_input] = qs
            for qi, q in enumerate(st.session_state["cached_questions"].get(db_url_input, [])[:5]):
                if st.button(q, width='stretch', key=f"sidebar_sq_{qi}"):
                    st.session_state["prefill"] = q

    # ── Multi-Connection Manager ──
    if is_connected and user_tables:
        st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
        with st.expander("🔗 Saved Connections", expanded=False):
            if "saved_connections" not in st.session_state:
                st.session_state.saved_connections = {}
            conn_name = st.text_input("Connection name", placeholder="My DB", label_visibility="collapsed", key="conn_name_input")
            if conn_name and st.button("Save Current", key="save_conn"):
                st.session_state.saved_connections[conn_name] = db_url_input
                st.toast(f"Saved '{conn_name}'")
            if st.session_state.saved_connections:
                sel_conn = st.selectbox("Switch to", [""] + list(st.session_state.saved_connections.keys()), key="conn_switch")
                if sel_conn:
                    st.session_state["db_url_input"] = st.session_state.saved_connections[sel_conn]
                    st.session_state["conn_switch"] = ""
                    st.rerun()

    # ── Audit Log (collapsible) ──
    if is_connected:
        st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
        with st.expander("📋 Query Audit Log", expanded=False):
            log_entries = get_query_log(20)
            if log_entries:
                for entry in log_entries[:10]:
                    eid, q, qtype, umsg, rc, err, dur, ts = entry
                    label = f"`{q[:50]}{'...' if len(q)>50 else ''}`"
                    status = "✅" if not err else "❌"
                    st.markdown(f"{status} {label}  _{dur}ms_  `{ts}`", unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-state" style="padding:0.5rem;"><p style="color:var(--text2);font-size:0.75rem;">No queries yet</p></div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.7rem;color:var(--text2);text-align:center;margin-top:1rem;">⚡ Built with LangGraph · Groq · Streamlit · Plotly · SQLAlchemy</div>', unsafe_allow_html=True)

# ── Hero Section (shown when no data loaded) ──
has_data = bool(st.session_state.auto_dashboards) or bool(st.session_state.pinned_charts)
if not has_data:
    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)
    hero_col1, hero_col2, hero_col3 = st.columns([1, 2, 1])
    with hero_col2:
        st.markdown(f'''
        <div style="text-align:center;padding:1.5rem 1rem 0.5rem;">
            <div style="font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:800;
                        background:linear-gradient(135deg,var(--accent),var(--accent2),#e879f9);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
                        margin-bottom:0.5rem;">DataNova</div>
            <p style="font-size:1.1rem;color:var(--text2);max-width:500px;margin:0 auto 1rem;line-height:1.7;">
                AI-Powered Autonomous Business Intelligence Platform
            </p>
            <p style="font-size:0.9rem;color:var(--text2);opacity:0.7;max-width:420px;margin:0 auto 1.5rem;line-height:1.6;">
                Upload data, ask questions in natural language, and generate dashboards, insights, and executive summaries instantly.
            </p>
            <p style="font-size:0.85rem;color:#9ea8ff;font-weight:600;margin-bottom:1.2rem;letter-spacing:0.04em;">
                Upload → Ask → Analyze → Visualize
            </p>
        </div>
        ''', unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            if st.button("📁 Upload Data", width='stretch', type="primary", key="hero_upload"):
                st.session_state.selected_tab = "📁 Data"
                st.rerun()
        with c2:
            if st.button("✨ Try Demo Dataset", width='stretch', key="hero_demo"):
                st.session_state["load_demo"] = True
                st.session_state.selected_tab = "📁 Data"
                st.rerun()

    st.markdown(f'''
    <div style="display:flex;justify-content:center;gap:0.75rem;flex-wrap:wrap;margin:0.8rem 0 0;">
        <span style="font-size:0.7rem;padding:0.2rem 0.7rem;background:var(--card);border:1px solid var(--card-border);border-radius:20px;color:var(--text2);">⚡ LangGraph + Groq</span>
        <span style="font-size:0.7rem;padding:0.2rem 0.7rem;background:var(--card);border:1px solid var(--card-border);border-radius:20px;color:var(--text2);">📊 Auto dashboards</span>
        <span style="font-size:0.7rem;padding:0.2rem 0.7rem;background:var(--card);border:1px solid var(--card-border);border-radius:20px;color:var(--text2);">🔒 Safe SQL execution</span>
        <span style="font-size:0.7rem;padding:0.2rem 0.7rem;background:var(--card);border:1px solid var(--card-border);border-radius:20px;color:var(--text2);">📁 CSV · Excel · SQLite</span>
    </div>
    ''', unsafe_allow_html=True)

    # ── Suggested first prompts ──
    st.markdown('<p style="font-size:0.75rem;color:var(--text2);text-align:center;margin:1.2rem 0 0.4rem;">Try asking:</p>', unsafe_allow_html=True)
    prompt_chips = ["Show revenue trends", "Analyze customer behavior", "Compare category performance", "Detect anomalies"]
    chip_cols = st.columns(len(prompt_chips), gap="small")
    for ci, chip in enumerate(prompt_chips):
        with chip_cols[ci]:
            if st.button(chip, key=f"onboard_chip_{ci}", use_container_width=True):
                st.session_state.selected_tab = "💬 Chat"
                st.session_state["prefill"] = chip
                st.rerun()

# ── Custom Tabs (programmatic switching) ──
tab_labels = ["💬 Chat", "📁 Data", "📊 Dashboard"]
tab_cols = st.columns(3, gap="small")
for i, label in enumerate(tab_labels):
    with tab_cols[i]:
        active = st.session_state.selected_tab == label
        btn_style = "primary" if active else "secondary"
        if st.button(label, key=f"tab_btn_{i}", type=btn_style, use_container_width=True):
            st.session_state.selected_tab = label
            st.rerun()

# ── Feature cards (landing state) ──
if not has_data:
    fc1, fc2, fc3 = st.columns(3, gap="small")
    with fc1:
        st.markdown(f'''<div class="feature-card">
            <div style="font-size:2rem;margin-bottom:0.3rem;">🧠</div>
            <div style="font-weight:600;font-size:0.85rem;">AI SQL Generation</div>
            <div style="font-size:0.7rem;color:var(--text2);margin-top:0.2rem;">Natural language to queries</div>
        </div>''', unsafe_allow_html=True)
    with fc2:
        st.markdown(f'''<div class="feature-card">
            <div style="font-size:2rem;margin-bottom:0.3rem;">📊</div>
            <div style="font-weight:600;font-size:0.85rem;">Auto Dashboards</div>
            <div style="font-size:0.7rem;color:var(--text2);margin-top:0.2rem;">KPIs, charts, insights</div>
        </div>''', unsafe_allow_html=True)
    with fc3:
        st.markdown(f'''<div class="feature-card">
            <div style="font-size:2rem;margin-bottom:0.3rem;">⚡</div>
            <div style="font-weight:600;font-size:0.85rem;">Executive Insights</div>
            <div style="font-size:0.7rem;color:var(--text2);margin-top:0.2rem;">AI-powered summaries</div>
        </div>''', unsafe_allow_html=True)
    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# TAB: CHAT
# ════════════════════════════════════════════════════
if st.session_state.selected_tab == "💬 Chat":
    chat_col, result_col = st.columns([0.55, 1], gap="small")

    with chat_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">💬 AI Chat</p>', unsafe_allow_html=True)
        for i, msg in enumerate(st.session_state.messages):
            is_last = (i == len(st.session_state.messages) - 1)
            if is_last and msg.get("pending_execution"):
                continue
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "⚡"):
                if msg["role"] == "user":
                    st.markdown(msg["content"])
                else:
                    is_python = msg.get("is_python_task", False)
                    if is_python:
                        st.markdown('<span class="tag">Python</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="sql-box">{msg.get("python_code")}</div>', unsafe_allow_html=True)
                    elif msg.get("sql"):
                        st.markdown('<span class="tag">SQL</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="sql-box">{msg["sql"]}</div>', unsafe_allow_html=True)
                    if msg.get("explanation"):
                        st.caption(f"💡 {msg['explanation']}")
                    if msg.get("error"):
                        st.markdown(f'<div class="error-box">⚠ {msg["error"]}</div>', unsafe_allow_html=True)

        # Pending HITL
        if st.session_state.messages:
            last_msg = st.session_state.messages[-1]
            if last_msg["role"] == "assistant" and last_msg.get("pending_execution"):
                with st.chat_message("assistant", avatar="⚡"):
                    is_python = last_msg.get("is_python_task", False)
                    code_type = "Python" if is_python else "SQL"
                    code_val = last_msg.get("python_code" if is_python else "sql", "")
                    explanation = last_msg.get("explanation", "")
                    
                    st.markdown(f'''
                    <div class="glass-card" style="padding:1.25rem;margin-bottom:0.5rem;border-left:3px solid var(--accent);">
                        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.75rem;">
                            <div style="width:8px;height:8px;border-radius:50%;background:var(--accent);animation:pulse 2s infinite;"></div>
                            <span style="font-weight:700;font-size:0.95rem;">Ready to Execute</span>
                            <span class="tag" style="margin-left:auto;">{code_type}</span>
                        </div>
                        {f'<div style="font-size:0.8rem;color:var(--text2);margin-bottom:0.75rem;padding-left:0.5rem;border-left:2px solid var(--card-border);">{explanation}</div>' if explanation else ''}
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    edited_code = st.text_area(
                        f"Edit {code_type} if needed",
                        value=code_val,
                        height=140,
                        label_visibility="collapsed",
                        key=f"edit_code_{len(st.session_state.messages) - 1}"
                    )
                    
                    btn_col1, btn_col2, btn_col3 = st.columns([3, 1.5, 1], gap="small")
                    with btn_col1:
                        if st.button("▶ Execute Query", type="primary", width='stretch', key="exec_primary"):
                            if is_python:
                                last_msg["python_code"] = edited_code
                            else:
                                last_msg["sql"] = edited_code
                            last_msg["pending_execution"] = False
                            with st.spinner("Executing..."):
                                t0 = time.time()
                                try:
                                    if is_python:
                                        exec_res = run_execution(sql="", db_url=db_url_input, is_python_task=True, python_code=edited_code)
                                    else:
                                        exec_res = run_execution(sql=edited_code, db_url=db_url_input)
                                except Exception as e:
                                    exec_res = {"final_result": None, "chart_spec": None, "error_message": f"Execution crashed: {str(e)}"}
                            last_msg["df"] = exec_res.get("final_result")
                            last_msg["chart_spec"] = exec_res.get("chart_spec")
                            last_msg["error"] = exec_res.get("error_message")
                            duration = int((time.time() - t0) * 1000)
                            register_query_log(
                                query=edited_code,
                                query_type="python" if is_python else "sql",
                                user_message=st.session_state.messages[-2]["content"] if len(st.session_state.messages) >= 2 else "",
                                row_count=len(exec_res.get("final_result", [])) if exec_res.get("final_result") is not None else 0,
                                error=exec_res.get("error_message", ""),
                                duration_ms=duration
                            )
                            st.rerun()
                    with btn_col2:
                        if st.button("📋 Copy", width='stretch', key="exec_copy"):
                            st.toast(f"{code_type} copied!", icon="")
                            st.session_state["copy_buffer"] = edited_code
                    with btn_col3:
                        if st.button("✕", width='stretch', key="exec_cancel", help="Discard"):
                            st.session_state.messages.pop()
                            st.rerun()

        # Chat input
        prefill = st.session_state.pop("prefill", "")
        question = st.chat_input("Ask anything about your data...", key="chat_input")
        if prefill and not question:
            question = prefill
        if question:
            if not os.environ.get("GROQ_API_KEY"):
                st.warning("Set GROQ_API_KEY in .env")
                st.stop()
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(question)
            with st.chat_message("assistant", avatar="⚡"):
                ai_ph = st.empty()
                ai_thinking_placeholder(ai_ph, ["🧠 Understanding schema...", "⚡ Generating SQL...", "🔍 Validating query...", "📊 Building response..."])
                try:
                    gen_res = run_generation(question, st.session_state.messages[:-1], db_url_input, data_dictionary)
                except Exception as e:
                    gen_res = {"error_message": f"Generation failed: {str(e)}", "sql_query": "", "python_code": "", "is_python_task": False, "sql_explanation": ""}
                ai_ph.empty()
                sql = gen_res.get("sql_query", "")
                python_code = gen_res.get("python_code", "")
                is_python = gen_res.get("is_python_task", False)
                explanation = gen_res.get("sql_explanation", "")
                error = gen_res.get("error_message", "")
                pending = (is_python and python_code and not error) or (sql and not error)
                st.session_state.messages.append({
                    "role": "assistant",
                    "sql": sql, "python_code": python_code, "is_python_task": is_python,
                    "explanation": explanation, "error": error, "pending_execution": pending,
                })
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    with result_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">📊 Results</p>', unsafe_allow_html=True)
        if st.session_state.messages:
            last = st.session_state.messages[-1]
            if last["role"] == "assistant" and not last.get("pending_execution"):
                df = last.get("df")
                if df is not None and len(df) > 0:
                    st.success(f"{len(df)} rows returned")
                    render_dynamic_chart(df, last.get("chart_spec"), key="result_chart")
                    with st.expander("View Data", expanded=False):
                        st.dataframe(df, width='stretch', height=200)
                    csv = df.to_csv(index=False)
                    st.download_button("📥 CSV", csv, f"export_{int(time.time())}.csv", "text/csv", width='stretch')
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("📌 Pin", width='stretch'):
                            q = ""
                            for m in reversed(st.session_state.messages[:-1]):
                                if m["role"] == "user":
                                    q = m["content"]; break
                            st.session_state.pinned_charts.append({
                                "id": str(uuid.uuid4()), "question": q,
                                "sql": last.get("python_code") if last.get("is_python_task") else last.get("sql"),
                                "df": df, "chart_spec": last.get("chart_spec")
                            })
                            st.toast("Pinned!")
                    with bc2:
                        if st.button("📊 Dashboard", width='stretch', key="create_dash_from_result"):
                            dash = {
                                "title": "Chat Dashboard",
                                "table_name": "",
                                "kpis": [{"label": "Rows", "value": len(df), "format": "number", "icon": "📊"}],
                                "charts": [{"title": "Result Chart", "df": df, "type": (last.get("chart_spec") or {}).get("type", "bar"), "x": (last.get("chart_spec") or {}).get("x", df.columns[0]), "y": (last.get("chart_spec") or {}).get("y", df.columns[1] if len(df.columns) > 1 else df.columns[0]), "is_main": True, "sql": ""}],
                                "summary": "Auto-generated from chat result.",
                                "suggested_questions": []
                            }
                            st.session_state.auto_dashboards["Chat Dashboard"] = dash
                            st.session_state.selected_dashboard = "Chat Dashboard"
                            st.toast("Dashboard created! Switch to 📊 Dashboard tab.")
                elif df is not None and len(df) == 0:
                    st.markdown('<div class="info-box">ℹ Query returned 0 rows</div>', unsafe_allow_html=True)
                elif last.get("error"):
                    st.markdown(f'<div class="error-box">⚠ {last["error"]}</div>', unsafe_allow_html=True)
            if last.get("pending_execution"):
                st.markdown('<div class="info-box">✋ Review the generated SQL in the chat panel, then execute or cancel.</div>', unsafe_allow_html=True)
        if not st.session_state.messages:
            st.markdown('<div class="empty-state"><p style="color:var(--text2);">Ask a question to see results here</p></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# TAB: DATA
# ════════════════════════════════════════════════════
if st.session_state.selected_tab == "📁 Data":
    # ── Auto-load demo dataset ──
    if st.session_state.pop("load_demo", False):
        demo_path = "sample_restaurant_data.csv"
        if os.path.exists(demo_path):
            with st.spinner("Loading demo dataset..."):
                df_demo = pd.read_csv(demo_path)
                tn = "restaurant_tips"
                dbc = get_cached_connector(db_url_input)
                dbc.upload_dataframe(df_demo, tn)
                register_upload(tn, demo_path, len(df_demo))
                st.success(f"Demo dataset loaded: {len(df_demo)} rows")
                with st.spinner("Analyzing data insights..."):
                    try:
                        insights = analyze_data_insights(df_demo, tn, db_url_input)
                    except Exception as e:
                        st.warning(f"Insight generation failed: {e}")
                        insights = ["Data loaded successfully. Ask questions in the Chat tab."]
                with st.expander("💡 Data Insights", expanded=True):
                    render_insight_cards(insights)
                get_cached_tables.clear()
                get_cached_schema.clear()
                st.session_state["cached_questions"].pop(db_url_input, None)
                try:
                    dash = auto_generate_dashboard(tn, db_url_input)
                except Exception as e:
                    st.warning(f"Auto-dashboard failed: {e}")
                    dash = None
                st.session_state.auto_dashboards[tn] = dash
                st.session_state.selected_dashboard = tn
                st.rerun()
        else:
            st.error("Demo file not found. Upload a CSV manually.")

    st.markdown('<p class="section-title">📁 Upload Data</p>', unsafe_allow_html=True)
    with st.expander("🌐 Fetch from URL", expanded=False):
        url = st.text_input("URL to CSV/JSON/Excel", placeholder="https://example.com/data.csv", label_visibility="collapsed")
        if url:
            try:
                with st.spinner("Fetching..."):
                    resp = requests.get(url, timeout=30)
                    resp.raise_for_status()
                    ct = resp.headers.get("content-type", "")
                    ul = url.lower()
                    if ".csv" in ul or "text/csv" in ct:
                        df_preview = pd.read_csv(io.StringIO(resp.text))
                    elif ".json" in ul or "application/json" in ct:
                        jd = resp.json()
                        if isinstance(jd, list): df_preview = pd.DataFrame(jd)
                        elif isinstance(jd, dict):
                            for k, v in jd.items():
                                if isinstance(v, list): df_preview = pd.DataFrame(v); break
                            else: df_preview = pd.DataFrame([jd])
                    elif ".xlsx" in ul or ".xls" in ul:
                        df_preview = pd.read_excel(io.BytesIO(resp.content))
                    else:
                        try: df_preview = pd.read_csv(io.StringIO(resp.text))
                        except Exception:
                            tables = pd.read_html(io.StringIO(resp.text))
                            df_preview = tables[0]
                    st.success(f"{len(df_preview)} rows")
                    st.dataframe(df_preview.head(10), width='stretch')
                    fname = sanitize_table_name(url.split("/")[-1]) or "web_data"
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        tn = st.text_input("Table name", value=fname, key="web_tn")
                    with c2:
                        if st.button("Add to Database", type="primary", width='stretch'):
                            dbc = get_cached_connector(db_url_input)
                            dbc.upload_dataframe(df_preview, tn)
                            register_upload(tn, url, len(df_preview))
                            st.success(f"Table '{tn}' created!")
                            with st.spinner("Analyzing data insights..."):
                                try:
                                    insights = analyze_data_insights(df_preview, tn, db_url_input)
                                except Exception as e:
                                    st.warning(f"Insights failed: {e}")
                                    insights = ["Data loaded."]
                            with st.expander("💡 Data Insights", expanded=True):
                                render_insight_cards(insights)
                            get_cached_tables.clear()
                            get_cached_schema.clear()
                            st.session_state["cached_questions"].pop(db_url_input, None)
                            try:
                                dash = auto_generate_dashboard(tn, db_url_input)
                            except Exception as e:
                                st.warning(f"Auto-dashboard failed: {e}")
                                dash = None
                            st.session_state.selected_dashboard = tn
                            st.rerun()
            except Exception as e:
                st.error(f"Fetch failed: {e}")

    uploaded_file = st.file_uploader("CSV / Excel (max 50MB)", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        if uploaded_file.size > 50 * 1024 * 1024:
            st.error("File too large. Maximum size is 50MB.")
            st.stop()
        temp_path = None
        try:
            fb = uploaded_file.read()
            ext = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(fb); temp_path = tmp.name
            tn = sanitize_table_name(uploaded_file.name)
            df_preview = pd.read_csv(temp_path) if ext.lower() == ".csv" else pd.read_excel(temp_path)
            st.success(f"{len(df_preview)} rows, {len(df_preview.columns)} cols")
            st.dataframe(df_preview.head(10), width='stretch')
            c1, c2 = st.columns([1, 2])
            with c1:
                ftn = st.text_input("Table name", value=tn)
            with c2:
                if st.button("Add to Database", type="primary", width='stretch'):
                    dbc = get_cached_connector(db_url_input)
                    dbc.upload_dataframe(df_preview, ftn)
                    register_upload(ftn, uploaded_file.name, len(df_preview))
                    st.success(f"Table '{ftn}' created!")
                    with st.spinner("Analyzing data insights..."):
                        try:
                            insights = analyze_data_insights(df_preview, ftn, db_url_input)
                        except Exception as e:
                            st.warning(f"Insights failed: {e}")
                            insights = ["Data loaded."]
                    with st.expander("💡 Data Insights", expanded=True):
                        render_insight_cards(insights)
                    get_cached_tables.clear()
                    get_cached_schema.clear()
                    st.session_state["cached_questions"].pop(db_url_input, None)
                    try:
                        dash = auto_generate_dashboard(ftn, db_url_input)
                    except Exception as e:
                        st.warning(f"Auto-dashboard failed: {e}")
                        dash = None
                    st.session_state.auto_dashboards[ftn] = dash
                    st.session_state.selected_dashboard = ftn
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    st.divider()
    st.markdown('<p class="section-title" style="margin-top:0.5rem;">Your Tables</p>', unsafe_allow_html=True)
    dbc = get_cached_connector(db_url_input)
    tbls = get_cached_tables(db_url_input)
    ut = [t for t in tbls if not t.startswith("_")]
    if ut:
        for t in ut:
            with st.expander(f"📊 {t}"):
                try:
                    dft = dbc.execute_query(f"SELECT * FROM [{t}] LIMIT 50")
                    st.dataframe(dft, width='stretch')
                    prof_tab, col_tab = st.tabs(["📊 Profile", "🔬 Columns"])
                    with prof_tab:
                        if st.button(f"Run Profile on {t}", key=f"prof_{t}"):
                            with st.spinner("Profiling..."):
                                dft_full = dbc.execute_query(f"SELECT * FROM [{t}]")
                                prof_stats = {}
                                for col in dft_full.columns:
                                    s = dft_full[col]
                                    entry = {"dtype": str(s.dtype), "nulls": int(s.isna().sum()), "null_pct": round(s.isna().mean() * 100, 1), "unique": int(s.nunique())}
                                    if pd.api.types.is_numeric_dtype(s):
                                        entry.update({"min": round(float(s.min()), 2), "max": round(float(s.max()), 2), "mean": round(float(s.mean()), 2), "median": round(float(s.median()), 2), "std": round(float(s.std()), 2)})
                                    prof_stats[col] = entry
                                st.session_state[f"_prof_{t}"] = prof_stats
                                st.session_state[f"_numcols_{t}"] = [c for c in dft_full.columns if pd.api.types.is_numeric_dtype(dft_full[c])]
                                st.session_state[f"_dft_{t}"] = dft_full
                        prof_stats = st.session_state.get(f"_prof_{t}")
                        if prof_stats:
                            dft_full = st.session_state.get(f"_dft_{t}")
                            prof_df = pd.DataFrame(prof_stats).T
                            st.dataframe(prof_df, width='stretch')
                            num_cols = st.session_state.get(f"_numcols_{t}", [])
                            if len(num_cols) >= 2 and dft_full is not None:
                                st.markdown("##### 🔥 Correlation Heatmap")
                                corr = dft_full[num_cols].corr()
                                fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", aspect="auto", height=400)
                                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="var(--text2)"))
                                st.plotly_chart(fig, use_container_width=True, key=f"corr_{t}")
                            hist_cols = st.multiselect("Histograms", num_cols, default=num_cols[:min(3, len(num_cols))], key=f"hist_sel_{t}")
                            if hist_cols and dft_full is not None:
                                for hc in hist_cols:
                                    fig_h = px.histogram(dft_full, x=hc, title=hc, height=250)
                                    fig_h.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="var(--text2)"))
                                    st.plotly_chart(fig_h, use_container_width=True, key=f"hist_{t}_{hc}")
                    with col_tab:
                        cols_info = dbc.get_table_schema(t)
                        st.json(cols_info)
                except Exception as e:
                    st.error(str(e))
    else:
        st.markdown('<div class="empty-state"><div style="font-size:2rem;margin-bottom:0.5rem;">📂</div><p style="color:var(--text2);">Upload your first dataset above to begin analysis</p></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# TAB: DASHBOARD
# ════════════════════════════════════════════════════
if st.session_state.selected_tab == "📊 Dashboard":
    has_auto = bool(st.session_state.auto_dashboards)
    has_pinned = bool(st.session_state.pinned_charts)

    if not has_auto and not has_pinned:
        st.markdown('<div class="empty-state"><div style="font-size:2.5rem;margin-bottom:0.5rem;">📊</div><h4>No Dashboards Yet</h4><p style="color:var(--text2);">Upload a dataset in <b>Data</b> tab to auto-generate a dashboard, or pin charts from <b>Chat</b>.</p></div>', unsafe_allow_html=True)

    if has_auto:
        dash_names = list(st.session_state.auto_dashboards.keys())
        if len(dash_names) > 1:
            selected = st.selectbox("Dashboard", dash_names,
                index=dash_names.index(st.session_state.selected_dashboard) if st.session_state.selected_dashboard in dash_names else 0)
            st.session_state.selected_dashboard = selected
        else:
            selected = dash_names[0]

        dash = st.session_state.auto_dashboards[selected]

        # Dashboard header
        title = dash.get('title', selected)
        st.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;"><h3 style="margin:0;">📊 {title}</h3><span style="font-size:0.8rem;color:var(--text2);">{len(dash.get("kpis",[]))} KPIs · {len(dash.get("charts",[]))} charts</span></div>', unsafe_allow_html=True)

        if dash.get("error"):
            st.markdown(f'<div class="error-box">⚠ {dash["error"]}</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)
        db_dash = get_cached_connector(db_url_input)
        table_name = dash.get("table_name", selected)

        # ── Always-visible Filters ──
        filter_cols = []
        try:
            inspector = inspect(db_dash.engine)
            for col in inspector.get_columns(table_name):
                if str(col["type"]).upper() in ("TEXT", "VARCHAR"):
                    filter_cols.append(col["name"])
        except Exception as e:
            st.warning(f"Inspector error: {e}")

        active_filter = None
        if filter_cols:
            st.markdown('<p class="section-title" style="margin-bottom:0;">🔍 Filters</p>', unsafe_allow_html=True)
            fcols = st.columns(min(len(filter_cols), 5))
            for fi, fc in enumerate(filter_cols[:5]):
                with fcols[fi]:
                    try:
                        dv = pd.read_sql(f"SELECT DISTINCT [{fc}] FROM [{table_name}] ORDER BY [{fc}]", db_dash.engine)
                        opts = ["All"] + [str(v) for v in dv.iloc[:, 0].tolist()]
                        sel = st.selectbox(fc, opts, key=f"f_{selected}_{fc}", label_visibility="collapsed")
                        if sel != "All":
                            active_filter = (fc, sel)
                    except Exception as e:
                        st.warning(f"Filter load error: {e}")

        st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)

        # ── KPI Row ──
        if dash.get("kpis"):
            kpi_list = dash["kpis"]
            kpi_values = []
            for kpi in kpi_list:
                if active_filter and kpi.get("sql"):
                    try:
                        fcol, fval = active_filter
                        df_k = pd.read_sql(_apply_filter(kpi["sql"], active_filter), db_dash.engine, params={"fv": fval})
                        val = round(float(df_k.iloc[0, 0]), 2) if df_k is not None and len(df_k) > 0 else None
                    except Exception:
                        val = kpi.get("value")
                else:
                    val = kpi.get("value")
                kpi_values.append(val)

            kpi_cols = st.columns(len(kpi_list))
            for i, kpi in enumerate(kpi_list):
                with kpi_cols[i]:
                    render_kpi_card(
                        kpi["label"], kpi_values[i],
                        trend=kpi.get("trend"),
                        icon=kpi.get("icon"),
                        fmt=kpi.get("format", "number")
                    )

        st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)

        # ── Main Chart + Data Quality side by side ──
        if dash.get("charts"):
            chart_list = [c for c in dash["charts"] if c.get("df") is not None and len(c["df"]) > 0]
            if chart_list:
                for chart in chart_list:
                    if active_filter and chart.get("sql"):
                        try:
                            fcol, fval = active_filter
                            chart["df"] = pd.read_sql(_apply_filter(chart["sql"], table_name, active_filter), db_dash.engine, params={"fv": fval})
                        except Exception:
                            pass

                main_chart = None
                secondary = []
                for c in chart_list:
                    if c.get("is_main") and main_chart is None:
                        main_chart = c
                    else:
                        secondary.append(c)
                if main_chart is None and chart_list:
                    main_chart = chart_list[0]
                    secondary = chart_list[1:]

                if main_chart is not None:
                    mc, dq = st.columns([2.5, 1], gap="small")
                    with mc:
                        st.markdown(f'<div class="chart-card"><div class="chart-title">{main_chart["title"]}</div>', unsafe_allow_html=True)
                        render_dynamic_chart(
                            main_chart["df"],
                            {"type": main_chart["type"], "x": main_chart["x"], "y": main_chart["y"]},
                            key=f"dm_{selected}"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                    with dq:
                        render_data_quality_panel(main_chart["df"])

                # Secondary charts grid (2 cols)
                if secondary:
                    for row_start in range(0, len(secondary), 2):
                        row_charts = secondary[row_start:row_start + 2]
                        scols = st.columns(2, gap="small")
                        for ci, chart in enumerate(row_charts):
                            with scols[ci]:
                                st.markdown(f'<div class="chart-card"><div class="chart-title">{chart["title"]}</div>', unsafe_allow_html=True)
                                render_dynamic_chart(
                                    chart["df"],
                                    {"type": chart["type"], "x": chart["x"], "y": chart["y"]},
                                    key=f"ds_{selected}_{row_start + ci}"
                                )
                                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)

        # ── Executive Summary + Suggested Qs ──
        ex, sq = st.columns([1.5, 1], gap="small")
        with ex:
            if dash.get("summary"):
                with st.expander("📝 Executive Summary", expanded=True):
                    st.markdown(f'<div class="exec-summary">{dash["summary"]}</div>', unsafe_allow_html=True)

        with sq:
            if dash.get("suggested_questions"):
                st.markdown('<p class="section-title" style="font-size:0.9rem;">💡 Suggested Questions</p>', unsafe_allow_html=True)
                for qi, q in enumerate(dash["suggested_questions"]):
                    if st.button(q, width='stretch', key=f"sq_{selected}_{qi}"):
                        st.session_state["prefill"] = q

        # ── AI Recommendations ──
        rec_key = f"dash_recs_{selected}"
        if rec_key not in st.session_state:
            with st.spinner("Generating recommendations..."):
                st.session_state[rec_key] = generate_recommendations(dash, db_url_input)
        recs = st.session_state[rec_key]
        if recs:
            st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)
            st.markdown('<p class="section-title" style="font-size:0.9rem;">🎯 AI Recommendations</p>', unsafe_allow_html=True)
            rec_cols = st.columns(min(len(recs), 3), gap="small")
            for ri, rec in enumerate(recs[:3]):
                with rec_cols[ri]:
                    st.markdown(f'<div style="padding:0.5rem 0.7rem;background:var(--card);border:1px solid var(--card-border);border-radius:12px;font-size:0.78rem;line-height:1.5;">{rec}</div>', unsafe_allow_html=True)

        # ── Dashboard Edit Chat ──
        st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)
        with st.expander("✏️ AI Dashboard Editor", expanded=False):
            for dm in st.session_state.dash_edit_messages[-6:]:
                if dm["role"] == "user":
                    st.markdown(f'<div style="padding:0.3rem 0;font-size:0.85rem;"><b>You:</b> {dm["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="padding:0.3rem 0;font-size:0.85rem;color:var(--accent);"><b>AI:</b> {dm["content"]}</div>', unsafe_allow_html=True)
            edit_req = st.chat_input("Ask to edit the dashboard...", key="dash_edit_input")
            if edit_req:
                st.session_state.dash_edit_messages.append({"role": "user", "content": edit_req})
                with st.spinner("Editing..."):
                    result = edit_dashboard(dash, edit_req, db_url_input)
                    action = result.get("action", "none")
                    msg = result.get("message", "")
                    if action == "none":
                        st.session_state.dash_edit_messages.append({"role": "assistant", "content": msg or "I can change chart types, add/remove KPIs, adjust titles, or modify the executive summary. Try something like 'make the main chart a line chart'."})
                    elif action == "multi":
                        steps = result.get("steps", [])
                        applied = []
                        for step in steps:
                            a = step.get("action")
                            if a == "modify_chart":
                                ci = step.get("chart_index")
                                chg = step.get("changes", {})
                                if ci is not None and ci < len(dash["charts"]):
                                    for k, v in chg.items():
                                        dash["charts"][ci][k] = v
                                    applied.append(f"Modified chart {ci}")
                            elif a == "add_kpi":
                                kpi = step.get("kpi", {})
                                dash.setdefault("kpis", []).append(kpi)
                                applied.append(f"Added KPI: {kpi.get('label')}")
                            elif a == "remove_kpi":
                                ki = step.get("kpi_index")
                                if ki is not None and ki < len(dash.get("kpis", [])):
                                    removed = dash["kpis"].pop(ki)
                                    applied.append(f"Removed KPI: {removed.get('label')}")
                            elif a == "add_chart":
                                nc = step.get("chart", {})
                                dash.setdefault("charts", []).append(nc)
                                applied.append(f"Added chart: {nc.get('title')}")
                            elif a == "set_summary":
                                dash["summary"] = step.get("summary", "")
                                applied.append("Updated summary")
                        st.session_state.auto_dashboards[selected] = dash
                        st.session_state.dash_edit_messages.append({"role": "assistant", "content": "Applied: " + ", ".join(applied) if applied else "No changes applied."})
                    elif action == "modify_chart":
                        ci = result.get("chart_index")
                        chg = result.get("changes", {})
                        if ci is not None and ci < len(dash["charts"]):
                            for k, v in chg.items():
                                dash["charts"][ci][k] = v
                            st.session_state.auto_dashboards[selected] = dash
                            st.session_state.dash_edit_messages.append({"role": "assistant", "content": f"Updated chart {ci}: {chg}"})
                    elif action == "add_kpi":
                        kpi = result.get("kpi", {})
                        dash.setdefault("kpis", []).append(kpi)
                        st.session_state.auto_dashboards[selected] = dash
                        st.session_state.dash_edit_messages.append({"role": "assistant", "content": f"Added KPI: {kpi.get('label')}"})
                    elif action == "remove_kpi":
                        ki = result.get("kpi_index")
                        if ki is not None and ki < len(dash.get("kpis", [])):
                            removed = dash["kpis"].pop(ki)
                            st.session_state.auto_dashboards[selected] = dash
                            st.session_state.dash_edit_messages.append({"role": "assistant", "content": f"Removed KPI: {removed.get('label')}"})
                    elif action == "add_chart":
                        nc = result.get("chart", {})
                        dash.setdefault("charts", []).append(nc)
                        st.session_state.auto_dashboards[selected] = dash
                        st.session_state.dash_edit_messages.append({"role": "assistant", "content": f"Added chart: {nc.get('title')}"})
                    elif action == "set_summary":
                        dash["summary"] = result.get("summary", "")
                        st.session_state.auto_dashboards[selected] = dash
                        st.session_state.dash_edit_messages.append({"role": "assistant", "content": "Executive summary updated."})
                    else:
                        st.session_state.dash_edit_messages.append({"role": "assistant", "content": f"Applied action: {action}"})
                st.rerun()

    # ── Pinned Charts ──
    if has_pinned:
        st.divider()
        pc, pd = st.columns([2, 1])
        with pc:
            st.markdown(f"##### 📌 Pinned Charts ({len(st.session_state.pinned_charts)})")
        with pd:
            if st.button("📄 Generate PDF Report", width='stretch'):
                with st.spinner("Writing report..."):
                    sm = generate_executive_summary(st.session_state.pinned_charts)
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", size=12)
                    pdf.multi_cell(0, 10, sm.encode('latin-1', 'replace').decode('latin-1'))
                    b = bytes(pdf.output())
                    st.download_button("📥 Download PDF", b, f"Report_{int(time.time())}.pdf", "application/pdf", type="primary")

        for idx, item in enumerate(st.session_state.pinned_charts):
            with st.container():
                st.markdown(f"**{item['question']}**")
                render_dynamic_chart(item["df"], item["chart_spec"], key=f"pin_{item['id']}")
                with st.expander("Data & Query", expanded=False):
                    st.code(item["sql"], language="sql")
                    st.dataframe(item["df"], width='stretch', height=120)
                if st.button("❌ Remove", key=f"rp_{item['id']}"):
                    st.session_state.pinned_charts.pop(idx)
                    st.rerun()
                st.divider()
