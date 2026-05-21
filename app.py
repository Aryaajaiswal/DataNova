"""
app.py  ·  Text-to-SQL Data Agent
Run:  streamlit run app.py
"""

import os
import io
import time
import tempfile
import uuid
import re
import requests
from dotenv import load_dotenv

load_dotenv()

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import inspect
from fpdf import FPDF

from agent import run_generation, run_execution, generate_sample_questions, generate_executive_summary, auto_generate_dashboard
from setup_db import create_database, DB_PATH, register_upload
from database import DatabaseConnector

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DataNova",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&family=Inter:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
    color: #1a1a2e;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.05); }
::-webkit-scrollbar-thumb { background: #6366f1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #4f46e5; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f9faff 100%) !important;
    border-right: 2px solid rgba(99, 102, 241, 0.1) !important;
    box-shadow: 2px 0 15px rgba(0,0,0,0.03) !important;
}
section[data-testid="stSidebar"] * { color: #2d3748 !important; }
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}

div[data-testid="stChatInput"] textarea {
    background: #ffffff !important;
    border: 2px solid #e5e7eb !important;
    border-radius: 16px !important;
    color: #1a1a2e !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 12px 16px !important;
    transition: all 0.3s ease !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    outline: none !important;
}
div[data-testid="stChatInput"] textarea::placeholder { color: #9ca3af !important; }

div[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border: 1px solid rgba(99, 102, 241, 0.1) !important;
    border-radius: 16px !important;
    padding: 1.25rem 1.5rem !important;
    margin-bottom: 1rem !important;
    color: #1a1a2e !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    backdrop-filter: blur(10px);
}
div[data-testid="stChatMessage"]:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.1) !important;
}

code, pre {
    font-family: 'Space Mono', monospace !important;
    background: linear-gradient(135deg, #f0f4ff 0%, #f8f9ff 100%) !important;
    color: #6366f1 !important;
    border-radius: 12px !important;
    font-size: 0.85rem !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(99, 102, 241, 0.1) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
}

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f9faff 100%);
    border: 1px solid rgba(99, 102, 241, 0.1);
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
div[data-testid="stMetricValue"] { color: #6366f1 !important; font-weight: 700 !important; }
div[data-testid="stMetricLabel"] { color: #6b7280 !important; font-size: 0.875rem !important; }

button { transition: all 0.3s ease !important; font-weight: 600 !important; }
button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
}
button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(99, 102, 241, 0.3) !important;
}

button[data-baseweb="tab"] {
    color: #6b7280 !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #6366f1 !important;
    border-bottom-color: #6366f1 !important;
    font-weight: 700 !important;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.5rem;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 0.5%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
    letter-spacing: -0.02em;
}

.hero-sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #6b7280;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 0.5rem;
    font-weight: 600;
}

.sql-box {
    background: linear-gradient(135deg, #f0f4ff 0%, #f8f9ff 100%);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-left: 4px solid #6366f1;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    color: #1a1a2e;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-x: auto;
}
.sql-box:hover {
    border-left-color: #8b5cf6;
    background: linear-gradient(135deg, #f3f0ff 0%, #faf8ff 100%);
}

.tag {
    display: inline-block;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.1) 100%);
    border: 1.5px solid #6366f1;
    color: #6366f1;
    border-radius: 20px;
    font-size: 0.7rem;
    padding: 4px 12px;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.05em;
    font-weight: 600;
    text-transform: uppercase;
}

.error-box {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(248, 113, 113, 0.05) 100%);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-left: 4px solid #ef4444;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    color: #991b1b;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
}

.success-box {
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(74, 222, 128, 0.05) 100%);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-left: 4px solid #22c55e;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    color: #15803d;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
}

.info-box {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(96, 165, 250, 0.05) 100%);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    color: #1e40af;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
}

hr {
    border: none !important;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.2), transparent) !important;
    margin: 2rem 0 !important;
}

button[data-testid="stExpanderToggleButton"] { color: #6366f1 !important; }

[role="status"] { border-radius: 12px !important; backdrop-filter: blur(10px) !important; }
</style>
""", unsafe_allow_html=True)


# ── DB bootstrap ──────────────────────────────────────────────────────────────
if not os.path.exists(DB_PATH):
    with st.spinner("Initializing database…"):
        create_database()

# ── Session State ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pinned_charts" not in st.session_state:
    st.session_state.pinned_charts = []
if "uploaded_tables" not in st.session_state:
    st.session_state.uploaded_tables = []
if "exploration_results" not in st.session_state:
    st.session_state.exploration_results = None
if "auto_dashboards" not in st.session_state:
    st.session_state.auto_dashboards = {}  # table_name -> dashboard dict
if "selected_dashboard" not in st.session_state:
    st.session_state.selected_dashboard = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ DataNova")
    st.divider()

    st.markdown("### 🔌 Database Connection")
    db_url = st.text_input("Database URI", value=f"sqlite:///{DB_PATH}", key="db_url_input")

    db_conn = DatabaseConnector(db_url)
    is_connected = db_conn.test_connection()
    if is_connected:
        st.success("Connection OK")
    else:
        st.error("Connection Failed — check the Database URI")

    st.divider()

    # ── Show uploaded tables ──
    st.markdown("### 📂 Your Tables")
    if is_connected:
        tables = db_conn.get_tables()
        user_tables = [t for t in tables if not t.startswith("_")]
        if user_tables:
            for t in user_tables:
                schema = db_conn.get_table_schema(t)
                st.markdown(f"- **{t}**")
                st.caption(f"  `{schema}`")
        else:
            st.caption("No tables yet. Upload data in the Data tab.")
    else:
        st.caption("Not connected.")

    st.divider()

    with st.expander("📖 Data Dictionary (Optional)", expanded=False):
        st.markdown("Define custom business rules here:")
        data_dictionary = st.text_area(
            "Rules",
            value="",
            height=100,
            placeholder="e.g. Revenue = price * quantity\nActive users = logged in within 30 days"
        )

    st.divider()

    st.markdown("### 💡 Sample Questions")
    if "cached_questions" not in st.session_state:
        st.session_state["cached_questions"] = {}

    if db_url not in st.session_state["cached_questions"]:
        if is_connected:
            with st.spinner("Analyzing dataset for sample questions..."):
                qs = generate_sample_questions(db_url)
                st.session_state["cached_questions"][db_url] = qs
        else:
            st.session_state["cached_questions"][db_url] = []

    sample_questions = st.session_state["cached_questions"].get(db_url, [])
    for qi, q in enumerate(sample_questions):
        if st.button(q, use_container_width=True, key=f"sample_{qi}"):
            st.session_state["prefill"] = q

    st.divider()
    st.markdown(
        "<div style='font-size:0.75rem;color:#9ca3af;font-family:Inter;text-align:center;line-height:1.6'>🚀 <b>Stack:</b> LangGraph · Groq · Llama-3.3 · SQLite<br/><br/><i>Upload your own data and ask questions</i></div>",
        unsafe_allow_html=True,
    )


# ── Main area (Tabs) ──────────────────────────────────────────────────────────
st.markdown('<p class="hero-title">⚡ DataNova</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Text-to-SQL Data Intelligence • Powered by LangGraph + Groq / Llama-3.3 • HITL Enabled</p>', unsafe_allow_html=True)
st.markdown("")

tab_chat, tab_data, tab_dash = st.tabs(["💬 Chat Explorer", "📁 My Data", "📌 My Dashboard"])


# ── Dynamic Chart Helper ─────────────────────────────────────────────────────
def auto_chart(df: pd.DataFrame):
    """Automatically pick a chart type based on data shape."""
    if len(df) < 2 or len(df.columns) < 2:
        return None
    num_cols = [c for c in df.columns if "int" in str(df[c].dtype) or "float" in str(df[c].dtype)]
    cat_cols = [c for c in df.columns if "object" in str(df[c].dtype) or "cate" in str(df[c].dtype)]
    if len(num_cols) >= 1 and len(cat_cols) >= 1:
        return px.bar(df, x=cat_cols[0], y=num_cols[0], color_discrete_sequence=["#6366f1"])
    if len(num_cols) >= 2:
        return px.line(df, x=num_cols[0], y=num_cols[1], color_discrete_sequence=["#6366f1"])
    if len(cat_cols) >= 2:
        return px.pie(df, names=cat_cols[0], color_discrete_sequence=["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"])
    return None

def _apply_chart_layout(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,255,0.5)",
        font_family="Inter",
        font_size=12,
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(99,102,241,0.2)",
            borderwidth=1
        )
    )

def render_dynamic_chart(df: pd.DataFrame, spec, key=None):
    if len(df) < 2 or len(df.columns) < 2:
        return None

    fig = None
    if spec is None:
        fig = auto_chart(df)
    elif hasattr(spec, "to_plotly_json"):
        fig = spec
    elif isinstance(spec, dict) and "type" in spec:
        chart_type = spec.get("type", "").lower()
        x_col = spec.get("x")
        y_col = spec.get("y")
        try:
            if chart_type == "bar" and x_col and y_col:
                fig = px.bar(df, x=x_col, y=y_col, color_discrete_sequence=["#6366f1"])
            elif chart_type == "line" and x_col and y_col:
                fig = px.line(df, x=x_col, y=y_col, color_discrete_sequence=["#6366f1"])
            elif chart_type == "scatter" and x_col and y_col:
                fig = px.scatter(df, x=x_col, y=y_col, color_discrete_sequence=["#6366f1"])
            elif chart_type == "pie" and x_col:
                fig = px.pie(df, names=x_col, values=y_col if y_col else None, color_discrete_sequence=["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"])
        except Exception:
            fig = auto_chart(df)

    if fig is None:
        fig = auto_chart(df)

    if fig:
        _apply_chart_layout(fig)
        st.plotly_chart(fig, use_container_width=True, config={"responsive": True, "displayModeBar": False}, key=key)
    return fig


def sanitize_table_name(name: str) -> str:
    """Convert filename to a valid SQL table name."""
    name = os.path.splitext(name)[0]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_').lower()
    if not name or name.upper() in {
        "SELECT", "FROM", "WHERE", "GROUP", "ORDER", "BY", "LIMIT",
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TABLE", "INTO", "VALUES", "SET", "AND", "OR", "NOT", "IN",
        "LIKE", "BETWEEN", "IS", "NULL", "AS", "ON", "JOIN", "LEFT",
        "RIGHT", "INNER", "OUTER", "FULL", "UNION", "ALL", "DISTINCT",
        "CASE", "WHEN", "THEN", "ELSE", "END", "EXISTS", "HAVING",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "ASC", "DESC",
    }:
        name = "uploaded_data"
    return name


def _apply_filter(sql: str, table: str, filt: tuple) -> str:
    """Inject a parameterized WHERE clause. Use with pd.read_sql(..., params={'fv': value})."""
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
    # Replace first ? placeholder or add AND
    if ":fv" not in sql:
        return sql.replace("WHERE ", f"WHERE [{col}] = :fv AND ")
    return sql



# ── Tab 1: Chat Explorer ──────────────────────────────────────────────────────
with tab_chat:
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
                    st.markdown('<span class="tag">Executed Python</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="sql-box">{msg.get("python_code")}</div>', unsafe_allow_html=True)
                elif msg.get("sql"):
                    st.markdown('<span class="tag">Executed SQL</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="sql-box">{msg["sql"]}</div>', unsafe_allow_html=True)
                st.markdown("")

                if msg.get("explanation"):
                    st.info(f"💡 **Explanation:** {msg['explanation']}")

                if msg.get("error"):
                    st.markdown(f'<div class="error-box">⚠ {msg["error"]}</div>', unsafe_allow_html=True)
                elif msg.get("df") is not None:
                    df: pd.DataFrame = msg["df"]
                    if len(df) == 0:
                        st.markdown('<div class="info-box">ℹ The query ran successfully but returned 0 rows. Try a different question or check if the table has matching data.</div>', unsafe_allow_html=True)
                    else:
                        st.success(f"✅ {len(df)} row{'s' if len(df) != 1 else ''} returned")
                    st.dataframe(df, use_container_width=True, height=min(400, 60 + len(df) * 36))

                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"datanova_export_{int(time.time())}.csv",
                        mime="text/csv",
                        key=f"dl_btn_{i}"
                    )

                    spec = msg.get("chart_spec")
                    render_dynamic_chart(df, spec, key=f"chart_chat_{i}")

                    st.divider()
                    if st.button("📌 Pin to Dashboard", key=f"pin_btn_{i}"):
                        st.session_state.pinned_charts.append({
                            "id": str(uuid.uuid4()),
                            "question": st.session_state.messages[i-1]["content"] if i > 0 else "Query Result",
                            "sql": msg.get("python_code") if msg.get("is_python_task") else msg.get("sql"),
                            "df": df,
                            "chart_spec": spec
                        })
                        st.toast("Chart pinned to your Dashboard!")

    if len(st.session_state.messages) > 0:
        last_msg = st.session_state.messages[-1]
        if last_msg["role"] == "assistant" and last_msg.get("pending_execution"):
            with st.chat_message("assistant", avatar="⚡"):
                st.info("✋ **Human-in-the-Loop:** Please review or edit the generated SQL before executing.")

                if last_msg.get("explanation"):
                    st.success(f"💡 **AI Explanation:** {last_msg['explanation']}")

                is_python = last_msg.get("is_python_task", False)
                if is_python:
                    edited_code = st.text_area("Python Script", value=last_msg.get("python_code", ""), height=250)
                else:
                    edited_code = st.text_area("SQL Query", value=last_msg.get("sql", ""), height=150)

                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("▶ Execute", type="primary"):
                        if is_python:
                            last_msg["python_code"] = edited_code
                        else:
                            last_msg["sql"] = edited_code
                        last_msg["pending_execution"] = False

                        with st.spinner("Executing..."):
                            t0 = time.time()
                            if is_python:
                                exec_res = run_execution(sql="", db_url=db_url, is_python_task=True, python_code=edited_code)
                            else:
                                exec_res = run_execution(sql=edited_code, db_url=db_url)
                            elapsed = time.time() - t0

                        last_msg["df"] = exec_res.get("final_result")
                        last_msg["chart_spec"] = exec_res.get("chart_spec")
                        last_msg["error"] = exec_res.get("error_message")
                        st.rerun()

                with col2:
                    if st.button("Cancel"):
                        st.session_state.messages.pop()
                        st.rerun()

    prefill = st.session_state.pop("prefill", "")

    question = st.chat_input("Ask anything about your data…", key="chat_input")

    if prefill and not question:
        question = prefill

    if question:
        if not os.environ.get("GROQ_API_KEY"):
            st.warning("Please set your GROQ_API_KEY in the .env file.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user", avatar="🧑"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="⚡"):
            with st.spinner("Thinking & generating SQL..."):
                try:
                    gen_res = run_generation(question, st.session_state.messages[:-1], db_url, data_dictionary)
                except Exception as e:
                    gen_res = {"error_message": f"Generation failed: {str(e)}", "sql_query": "", "python_code": "", "is_python_task": False, "sql_explanation": ""}

            sql = gen_res.get("sql_query", "")
            python_code = gen_res.get("python_code", "")
            is_python = gen_res.get("is_python_task", False)
            explanation = gen_res.get("sql_explanation", "")
            error = gen_res.get("error_message", "")

            pending = False
            if is_python and python_code and not error:
                pending = True
            elif sql and not error:
                pending = True

            st.session_state.messages.append({
                "role": "assistant",
                "sql": sql,
                "python_code": python_code,
                "is_python_task": is_python,
                "explanation": explanation,
                "error": error,
                "pending_execution": pending,
            })
            st.rerun()


# ── Tab 2: My Data (Upload & Manage) ──────────────────────────────────────────
with tab_data:
    st.markdown("### Upload Your Data")
    st.markdown("Upload CSV or Excel files, or fetch data from a URL.")

    # ── Web fetch ──
    with st.expander("🌐 Fetch from URL", expanded=False):
        url = st.text_input("Enter a URL pointing to a CSV, JSON, or Excel file", placeholder="https://example.com/data.csv")
        if url:
            try:
                with st.spinner("Fetching data..."):
                    import io, requests
                    resp = requests.get(url, timeout=30)
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "")
                    url_lower = url.lower()

                    if ".csv" in url_lower or "text/csv" in content_type:
                        df_preview = pd.read_csv(io.StringIO(resp.text))
                        source_name = url.split("/")[-1]
                    elif ".json" in url_lower or "application/json" in content_type:
                        json_data = resp.json()
                        if isinstance(json_data, list):
                            df_preview = pd.DataFrame(json_data)
                        elif isinstance(json_data, dict):
                            for k, v in json_data.items():
                                if isinstance(v, list):
                                    df_preview = pd.DataFrame(v)
                                    break
                            else:
                                df_preview = pd.DataFrame([json_data])
                        source_name = url.split("/")[-1]
                    elif ".xlsx" in url_lower or ".xls" in url_lower:
                        df_preview = pd.read_excel(io.BytesIO(resp.content))
                        source_name = url.split("/")[-1]
                    else:
                        try:
                            df_preview = pd.read_csv(io.StringIO(resp.text))
                            source_name = url.split("/")[-1]
                        except Exception:
                            try:
                                tables = pd.read_html(io.StringIO(resp.text))
                                df_preview = tables[0]
                                source_name = "html_table"
                            except Exception:
                                st.error("Could not parse response as CSV, JSON, or HTML table.")
                                st.stop()

                    st.success(f"Fetched: {len(df_preview)} rows, {len(df_preview.columns)} columns")
                    st.dataframe(df_preview.head(20), use_container_width=True)
                    col_info = ", ".join([f"{c} ({str(df_preview[c].dtype)})" for c in df_preview.columns])
                    st.caption(f"Columns: {col_info}")

                    fname = sanitize_table_name(source_name) or "web_data"
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        final_table_name = st.text_input("Table name", value=fname, key="web_table_name")
                    with col2:
                        if st.button("Add to Database", type="primary", use_container_width=True, key="web_add_btn"):
                            db_conn_w = DatabaseConnector(db_url)
                            db_conn_w.upload_dataframe(df_preview, final_table_name)
                            register_upload(final_table_name, url, len(df_preview))
                            st.success(f"Table '{final_table_name}' created with {len(df_preview)} rows!")
                            st.session_state.uploaded_tables.append(final_table_name)
                            st.session_state["cached_questions"].pop(db_url, None)
                            with st.spinner("Generating auto-dashboard..."):
                                dash = auto_generate_dashboard(final_table_name, db_url)
                                st.session_state.auto_dashboards[final_table_name] = dash
                                st.session_state.selected_dashboard = final_table_name
                            st.rerun()
            except Exception as e:
                st.error(f"Fetch failed: {e}")

    st.divider()

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
    )

    if uploaded_file is not None:
        temp_path = None
        try:
            file_bytes = uploaded_file.read()
            ext = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name

            table_name = sanitize_table_name(uploaded_file.name)

            if ext.lower() in (".csv",):
                df_preview = pd.read_csv(temp_path)
            else:
                df_preview = pd.read_excel(temp_path)

            st.success(f"Preview: {len(df_preview)} rows, {len(df_preview.columns)} columns")
            st.dataframe(df_preview.head(20), use_container_width=True)

            col_info = ", ".join([f"{c} ({str(df_preview[c].dtype)})" for c in df_preview.columns])
            st.caption(f"Columns: {col_info}")

            col1, col2 = st.columns([1, 3])
            with col1:
                final_table_name = st.text_input("Table name", value=table_name)
            with col2:
                if st.button("Add to Database", type="primary", use_container_width=True):
                    db_conn = DatabaseConnector(db_url)
                    db_conn.upload_dataframe(df_preview, final_table_name)
                    register_upload(final_table_name, uploaded_file.name, len(df_preview))
                    st.success(f"Table '{final_table_name}' created with {len(df_preview)} rows!")
                    st.session_state.uploaded_tables.append(final_table_name)
                    st.session_state["cached_questions"].pop(db_url, None)
                    with st.spinner("Generating auto-dashboard..."):
                        dash = auto_generate_dashboard(final_table_name, db_url)
                        st.session_state.auto_dashboards[final_table_name] = dash
                        st.session_state.selected_dashboard = final_table_name
                    st.rerun()

        except Exception as e:
            st.error(f"Error processing file: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    st.divider()

    st.markdown("### Your Uploaded Tables")
    db_conn = DatabaseConnector(db_url)
    tables = db_conn.get_tables()
    user_tables = [t for t in tables if not t.startswith("_")]

    if user_tables:
        for t in user_tables:
            with st.expander(f"📊 {t}"):
                try:
                    df_table = db_conn.execute_query(f"SELECT * FROM [{t}] LIMIT 50")
                    st.dataframe(df_table, use_container_width=True)
                    st.caption(f"{len(df_table)} rows shown (max 50)")
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("No tables yet. Upload a CSV or Excel file above to get started.")

    # ── Auto-generated dashboard inline preview ──
    if st.session_state.auto_dashboards:
        st.divider()
        st.markdown("### 📊 Auto-Generated Dashboards")
        st.caption("View full dashboards in the **📌 My Dashboard** tab.")
        for tname, dash in st.session_state.auto_dashboards.items():
            with st.expander(f"Dashboard: {tname}", expanded=False):
                if dash.get("error"):
                    st.warning(f"Issues: {dash['error']}")
                if dash.get("kpis"):
                    cols = st.columns(len(dash["kpis"]))
                    for i, kpi in enumerate(dash["kpis"]):
                        with cols[i]:
                            val = kpi.get("value")
                            if val is not None:
                                if kpi.get("format") == "currency":
                                    display = f"${val:,.2f}"
                                elif kpi.get("format") == "percent":
                                    display = f"{val:.1f}%"
                                elif kpi.get("format") == "integer":
                                    display = f"{int(val):,}"
                                else:
                                    display = f"{val:,.2f}"
                            else:
                                display = "N/A"
                            st.metric(label=kpi["label"], value=display)
                if dash.get("summary"):
                    st.caption(dash["summary"][:200] + "..." if len(dash["summary"]) > 200 else dash["summary"])

    # ── Auto-exploration results ──
    if st.session_state.exploration_results:
        with st.expander("🔍 View raw SQL discovery queries", expanded=False):
            for idx, res in enumerate(st.session_state.exploration_results):
                with st.container():
                    st.markdown(f"**{idx+1}. {res['question']}**")
                    st.code(res['sql'], language="sql")
                    if res.get("error"):
                        st.markdown(f'<div class="error-box">⚠ {res["error"]}</div>', unsafe_allow_html=True)
                    elif res.get("df") is not None:
                        df_r = res["df"]
                        st.dataframe(df_r, use_container_width=True)
                        render_dynamic_chart(df_r, None, key=f"explore_chart_{idx}")
                    st.divider()
            if st.button("Clear Exploration Results"):
                st.session_state.exploration_results = None
                st.rerun()


# ── Tab 3: Dashboard (PowerBI-like) ───────────────────────────────────────────
with tab_dash:
    has_auto = bool(st.session_state.auto_dashboards)
    has_pinned = bool(st.session_state.pinned_charts)

    if not has_auto and not has_pinned:
        st.markdown("""
        <div style='text-align:center;padding:3rem 1rem;'>
            <div style='font-size:3rem;margin-bottom:1rem;'>📊</div>
            <h3 style='color:#6b7280;font-weight:500;'>No Dashboards Yet</h3>
            <p style='color:#9ca3af;margin:1rem 0;'>Upload a dataset in <b>📁 My Data</b> to auto-generate a dashboard, or pin charts from the <b>💬 Chat Explorer</b>.</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Auto-generated dashboards ──
    if has_auto:
        dash_names = list(st.session_state.auto_dashboards.keys())

        # Dashboard selector
        if len(dash_names) > 1:
            sel_col1, sel_col2 = st.columns([1, 3])
            with sel_col1:
                selected = st.selectbox(
                    "Select Dashboard",
                    dash_names,
                    index=dash_names.index(st.session_state.selected_dashboard) if st.session_state.selected_dashboard in dash_names else 0,
                    key="dash_selector"
                )
                st.session_state.selected_dashboard = selected
            with sel_col2:
                st.markdown("")  # spacer
        else:
            selected = dash_names[0]

        dash = st.session_state.auto_dashboards[selected]
        db_conn_dash = DatabaseConnector(db_url)

        # ── Smart title ──
        st.markdown(f"## 📊 {dash.get('title', dash.get('table_name', selected))}")
        st.markdown(f"<p style='color:#6b7280;margin-top:-0.5rem;font-size:0.9rem;'>{len(dash.get('kpis', []))} KPIs · {len(dash.get('charts', []))} charts · table: <code>{dash.get('table_name')}</code></p>", unsafe_allow_html=True)

        if dash.get("error"):
            st.warning(f"Dashboard generation had issues: {dash['error']}")

        # ── Filters row ──
        table_name = dash.get("table_name", selected)
        filter_cols = []
        try:
            inspector = inspect(db_conn_dash.engine)
            for col in inspector.get_columns(table_name):
                if str(col["type"]).upper() in ("TEXT", "VARCHAR"):
                    filter_cols.append(col["name"])
        except Exception:
            pass

        active_filter = None
        if filter_cols:
            with st.expander("🔍 Filters", expanded=False):
                fcols = st.columns(len(filter_cols))
                for fi, fc in enumerate(filter_cols):
                    with fcols[fi]:
                        try:
                            distinct_sql = f"SELECT DISTINCT [{fc}] FROM [{table_name}] ORDER BY [{fc}]"
                            distinct_vals = pd.read_sql(distinct_sql, db_conn_dash.engine)
                            opts = ["All"] + [str(v) for v in distinct_vals.iloc[:, 0].tolist()]
                            sel_val = st.selectbox(fc, opts, key=f"filter_{selected}_{fc}")
                            if sel_val != "All":
                                active_filter = (fc, sel_val)
                        except Exception:
                            pass

        # ── KPI cards row ──
        if dash.get("kpis"):
            kpi_list = dash["kpis"]
            kpi_values = []
            for kpi in kpi_list:
                if active_filter and kpi.get("sql"):
                    try:
                        fcol, fval = active_filter
                        filtered_sql = _apply_filter(kpi["sql"], table_name, active_filter)
                        df_k = pd.read_sql(filtered_sql, db_conn_dash.engine, params={"fv": fval})
                        val = df_k.iloc[0, 0] if df_k is not None and len(df_k) > 0 else None
                        val = round(float(val), 2) if val is not None else None
                    except Exception:
                        val = kpi.get("value")
                else:
                    val = kpi.get("value")
                kpi_values.append(val)

            kpi_cols = st.columns(len(kpi_list))
            for i, kpi in enumerate(kpi_list):
                with kpi_cols[i]:
                    v = kpi_values[i]
                    if v is not None:
                        if kpi.get("format") == "currency":
                            display = f"${v:,.2f}"
                        elif kpi.get("format") == "percent":
                            display = f"{v:.1f}%"
                        elif kpi.get("format") == "integer":
                            display = f"{int(v):,}"
                        else:
                            display = f"{v:,.2f}"
                    else:
                        display = "N/A"
                    st.metric(label=kpi["label"], value=display, help=kpi.get("error", None))

        # ── Charts grid: main chart full-width, secondary in 2 cols ──
        if dash.get("charts"):
            chart_list = [c for c in dash["charts"] if c.get("df") is not None and len(c["df"]) > 0]
            if chart_list:
                # Re-execute charts with filter
                for chart in chart_list:
                    if active_filter and chart.get("sql"):
                        try:
                            fcol, fval = active_filter
                            fsql = _apply_filter(chart["sql"], table_name, active_filter)
                            chart["df"] = pd.read_sql(fsql, db_conn_dash.engine, params={"fv": fval})
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

                # Main chart (full width)
                if main_chart is not None:
                    st.markdown(f"**{main_chart['title']}**")
                    render_dynamic_chart(
                        main_chart["df"],
                        {"type": main_chart["type"], "x": main_chart["x"], "y": main_chart["y"]},
                        key=f"auto_dash_main_{selected}"
                    )

                # Secondary charts (2 columns)
                if secondary:
                    for row_start in range(0, len(secondary), 2):
                        row_charts = secondary[row_start:row_start + 2]
                        scols = st.columns(2)
                        for ci, chart in enumerate(row_charts):
                            with scols[ci]:
                                st.markdown(f"**{chart['title']}**")
                                render_dynamic_chart(
                                    chart["df"],
                                    {"type": chart["type"], "x": chart["x"], "y": chart["y"]},
                                    key=f"auto_dash_sec_{selected}_{row_start + ci}"
                                )

        # ── Executive summary ──
        if dash.get("summary"):
            with st.expander("📝 Executive Summary", expanded=True):
                st.info(dash["summary"])

        # ── Suggested follow-up questions ──
        if dash.get("suggested_questions"):
            st.markdown("### 💡 Suggested Next Questions")
            sqcols = st.columns(len(dash["suggested_questions"]))
            for qi, q in enumerate(dash["suggested_questions"]):
                with sqcols[qi]:
                    if st.button(q, use_container_width=True, key=f"suggested_{selected}_{qi}"):
                        st.session_state["prefill"] = q

        st.divider()

    # ── Pinned charts section ──
    if has_pinned:
        st.markdown("### 📌 Pinned Charts")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"{len(st.session_state.pinned_charts)} pinned chart{'s' if len(st.session_state.pinned_charts) != 1 else ''}")
        with col2:
            if st.button("📄 Generate PDF Report", use_container_width=True):
                with st.spinner("Writing report..."):
                    summary_md = generate_executive_summary(st.session_state.pinned_charts)
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", size=12)
                    text_clean = summary_md.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 10, text=text_clean)
                    pdf_bytes = bytes(pdf.output())
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"Executive_Report_{int(time.time())}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )

        for idx, item in enumerate(st.session_state.pinned_charts):
            with st.container():
                st.markdown(f"**{item['question']}**")
                render_dynamic_chart(item["df"], item["chart_spec"], key=f"pinned_{item['id']}")
                with st.expander("View Data & Query"):
                    st.code(item["sql"], language="sql")
                    st.dataframe(item["df"], use_container_width=True, height=150)
                if st.button("❌ Remove", key=f"remove_pin_{item['id']}"):
                    st.session_state.pinned_charts.pop(idx)
                    st.rerun()
                st.divider()
