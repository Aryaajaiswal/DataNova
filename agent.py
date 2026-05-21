"""
agent.py
LangGraph-powered Text-to-SQL agent for DataNova.
Features: Multi-turn memory, RAG schema extraction, Few-Shot examples, Dynamic charting.
"""

from __future__ import annotations

import os
import re
import json
from typing import TypedDict, Literal

import pandas as pd
from langgraph.graph import StateGraph, END
from groq import Groq

from database import DatabaseConnector

# ── Configuration ────────────────────────────────────────────────────────────
DB_PATH    = "datanova.db"
GROQ_MODEL = "llama-3.3-70b-versatile"
CHART_MODEL = "llama-3.1-8b-instant"

# ── Few-Shot Examples ────────────────────────────────────────────────────────
FEW_SHOT_EXAMPLES = """
Example 1:
Question: "Show total sales per category"
SQL: SELECT category, SUM(quantity_sold) AS total_sold, SUM(price * quantity_sold) AS total_revenue FROM your_table GROUP BY category ORDER BY total_revenue DESC;

Example 2:
Question: "What are the top 5 most popular items?"
SQL: SELECT item_name, SUM(quantity_sold) AS total_sold FROM your_table GROUP BY item_name ORDER BY total_sold DESC LIMIT 5;

Example 3:
Question: "Show sales trend over time"
SQL: SELECT order_date, SUM(quantity_sold) AS daily_sold, SUM(price * quantity_sold) AS daily_revenue FROM your_table GROUP BY order_date ORDER BY order_date;

IMPORTANT: Use the actual table and column names from the schema. Do NOT use 'your_table'. Always use real column names.
""".strip()

# ── Graph State ──────────────────────────────────────────────────────────────
class GraphState(TypedDict):
    db_url:          str
    data_dictionary: str
    user_question:   str
    chat_history:    list[dict]
    database_schema: str
    is_python_task:  bool
    python_code:     str
    sql_query:       str
    sql_explanation: str
    final_result:    pd.DataFrame | None
    chart_spec:      dict | None
    error_message:   str
    retry_count:     int


# ── Node 1 : Schema Extraction (Lightweight RAG) ─────────────────────────────
def extract_schema(state: GraphState) -> GraphState:
    """Query metadata and build schema, prioritizing relevant tables."""
    db = DatabaseConnector(state["db_url"])
    tables = db.get_tables()
    
    # Lightweight RAG: Check keyword overlap
    question_lower = state["user_question"].lower()
    
    relevant_tables = []
    for t in tables:
        # Simple keyword matching heuristic
        if t.lower() in question_lower or t.rstrip('s') in question_lower:
            relevant_tables.insert(0, t) # Prioritize
        else:
            relevant_tables.append(t)
            
    # Take top 5 most relevant to fit token limits context window
    schema_lines = []
    for t in relevant_tables[:5]:
        schema_lines.append("  " + db.get_table_schema(t))

    schema_str = "DATABASE SCHEMA:\n" + "\n".join(schema_lines)
    return {**state, "database_schema": schema_str, "error_message": ""}

# ── Node 1.5 : Intent Classification ─────────────────────────────────────────
def classify_intent(state: GraphState) -> GraphState:
    """Classify if the question requires SQL only or Python Data Science."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    client  = Groq(api_key=api_key)
    
    prompt = f"""
    Determine if the user's question requires advanced Python data science (forecasting, prediction, scikit-learn, complex stats) or can be answered with a standard SQL query.
    Default to SQL unless the question explicitly asks for forecasting, machine learning, regression, or statistical modeling.
    Question: {state['user_question']}
    Output JSON: {{"is_python": true}} or {{"is_python": false}}
    """
    try:
        res = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=15,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(res.choices[0].message.content)
        return {**state, "is_python_task": parsed.get("is_python", False)}
    except Exception:
        return {**state, "is_python_task": False}

# ── Node 2A : Python Code Generation ─────────────────────────────────────────
def generate_python(state: GraphState) -> GraphState:
    api_key = os.environ.get("GROQ_API_KEY", "")
    client  = Groq(api_key=api_key)

    system_prompt = (
        "You are an expert Data Scientist. Write a Python script to answer the user's data science/forecasting question. "
        "The script MUST define exactly this function: `def run_analysis(db_url: str):` "
        "Inside `run_analysis`, connect to SQLite using `sqlalchemy.create_engine(db_url)`, "
        "fetch data via `pd.read_sql()`, perform the analysis (using sklearn, pandas, etc.), and plot a Plotly figure. "
        "The function MUST return a tuple: `(df, fig)` where `df` is the final DataFrame and `fig` is the plotly figure object. "
        "CRITICAL RULES: "
        "1. Do NOT use matplotlib, plt.savefig, or any file I/O. Use ONLY plotly. "
        "2. Do NOT read or write any files. Do NOT use open(), savefig(), or to_csv() inside the script. "
        "3. Do NOT include any markdown, print statements, or image tags. Return ONLY the Plotly figure object. "
        "4. Use `fig.show()` is not needed — just return the fig. "
        "Output ONLY JSON: {'python_code': 'raw python code string', 'explanation': 'brief explanation'}."
    )
    user_prompt = f"SCHEMA:\n{state['database_schema']}\n\nQuestion: {state['user_question']}"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0,
            max_tokens=1024,
            timeout=20,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        code = parsed.get("python_code", "")
        code = re.sub(r"```python|```", "", code, flags=re.IGNORECASE).strip()

        # Safety strip: remove any file I/O or image save lines
        code = re.sub(r"plt\.savefig\(.*?\)\s*", "", code)
        code = re.sub(r"\.to_csv\(.*?\)\s*", "", code)
        code = re.sub(r"\.to_excel\(.*?\)\s*", "", code)
        code = re.sub(r"open\(.*?\)\s*", "", code)

        explanation = parsed.get("explanation", "")
        return {**state, "python_code": code, "sql_explanation": explanation}
    except Exception as e:
        return {**state, "error_message": str(e)}


# ── Node 2 : SQL Generation via Groq ─────────────────────────────────────────
def generate_sql(state: GraphState) -> GraphState:
    """Send schema + question + history to Groq and extract SQL."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    client  = Groq(api_key=api_key)

    dict_prompt = f"DATA DICTIONARY / RULES:\n{state['data_dictionary']}\n\n" if state.get("data_dictionary") else ""

    system_prompt = (
        "You are an expert SQL engineer. "
        "Given a database schema and a natural language question (and prior chat history), "
        "output ONLY a JSON object containing two keys: "
        "'sql' (the raw valid SQLite/SQL SELECT query ending with a semicolon) and "
        "'explanation' (a brief 1-2 sentence plain English explanation of what the query calculates).\n\n"
        f"{dict_prompt}"
        f"{FEW_SHOT_EXAMPLES}"
    )

    retry_note = ""
    if state.get("error_message"):
        retry_note = (
            f"\n\nPrevious attempt failed with error: {state['error_message']}\n"
            "Fix the query accordingly."
        )

    # Format chat history
    history_str = ""
    if state.get("chat_history"):
        history_str = "CHAT HISTORY:\n"
        # Only take last 4 messages to prevent context bloat
        for msg in state["chat_history"][-4:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg.get("content") or msg.get("sql") or msg.get("explanation") or "(no text)"
            history_str += f"{role}: {content}\n"
        history_str += "\n"

    user_prompt = (
        f"{state['database_schema']}\n\n"
        f"{history_str}"
        f"Question: {state['user_question']}"
        f"{retry_note}"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0,
            max_tokens=512,
            timeout=20,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        raw_sql = parsed.get("sql", "")
        explanation = parsed.get("explanation", "")
        raw_sql = re.sub(r"```sql|```", "", raw_sql, flags=re.IGNORECASE).strip()
        return {**state, "sql_query": raw_sql, "sql_explanation": explanation}
    except Exception as e:
        return {**state, "sql_query": "", "error_message": f"Failed to generate SQL: {str(e)}"}


import ast
import signal
import pandas as pd
import plotly.express as px
from groq import Groq
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Any
from database import DatabaseConnector

# ── Safe Python Execution ───────────────────────────────────────────────────
DANGEROUS_NODES = (
    ast.Import, ast.ImportFrom, ast.Call, ast.Attribute,
    ast.Subscript, ast.Await, ast.AsyncFor, ast.AsyncWith,
    ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal,
    ast.Delete, ast.Assert,
)

ALLOWED_BUILTIN_NAMES = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float",
    "int", "isinstance", "len", "list", "max", "min", "print",
    "range", "round", "sorted", "str", "sum", "tuple", "type",
    "zip", "map", "filter", "reversed", "set", "True", "False", "None",
}

ALLOWED_MODULE_NAMES = {"pandas", "numpy", "plotly", "math", "datetime", "statistics"}

def _validate_python_ast(code: str) -> Optional[str]:
    """Return error message if code contains dangerous patterns, else None."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax error: {e}"
    
    for node in ast.walk(tree):
        # Block imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] not in ALLOWED_MODULE_NAMES:
                    return f"Import of '{node.module}' is not allowed"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in ALLOWED_MODULE_NAMES:
                        return f"Import of '{alias.name}' is not allowed"
        
        # Block dangerous builtins via attribute access
        if isinstance(node, ast.Attribute):
            attr = node.attr
            if attr.startswith("__") and attr.endswith("__"):
                return f"Access to dunder attribute '{attr}' is not allowed"
            if attr in ("__class__", "__base__", "__subclasses__", "__mro__",
                        "__globals__", "__builtins__", "__import__", "system",
                        "popen", "exec", "eval", "compile", "open", "input"):
                return f"Access to '{attr}' is not allowed"
        
        # Block function calls to dangerous names
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in (
                "exec", "eval", "compile", "open", "input", "__import__",
                "getattr", "setattr", "delattr", "vars", "dir", "help",
            ):
                return f"Call to '{node.func.id}' is not allowed"
    
    return None

class TimeoutError(Exception):
    pass

def _timeout_handler(signum, frame):
    raise TimeoutError("Python execution timed out (10s limit)")

def _execute_sandboxed(code: str, db_url: str, timeout: int = 10) -> tuple:
    """Execute Python code in a restricted environment with timeout."""
    # AST validation first
    error = _validate_python_ast(code)
    if error:
        raise RuntimeError(f"Code validation failed: {error}")
    
    # Create restricted environment
    allowed_globals = {
        "__builtins__": {name: __builtins__[name] for name in ALLOWED_BUILTIN_NAMES if name in __builtins__},
        "pd": pd,
        "px": px,
        "np": __import__("numpy") if __import__("importlib").util.find_spec("numpy") else None,
    }
    
    local_vars = {}
    
    # Set timeout (Unix only, fallback for Windows)
    if hasattr(signal, "SIGALRM"):
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
    
    try:
        exec(compile(code, "<sandbox>", "exec"), allowed_globals, local_vars)
    except TimeoutError:
        raise RuntimeError("Python execution timed out")
    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    if "run_analysis" not in local_vars:
        raise RuntimeError("run_analysis function not found in generated code")
    
    result = local_vars["run_analysis"](db_url)
    if not isinstance(result, tuple) or len(result) != 2:
        raise RuntimeError("run_analysis must return (DataFrame, chart_spec)")
    
    return result

# ── Execution Nodes (Used manually via HITL or retries) ──────────────────────
def execute_python(state: GraphState) -> GraphState:
    """Execute the generated Python script in a restricted sandbox."""
    code = state["python_code"]
    try:
        df, fig = _execute_sandboxed(code, state["db_url"])
        return {**state, "final_result": df, "chart_spec": fig, "error_message": ""}
    except Exception as exc:
        return {**state, "error_message": f"Python Execution Error: {str(exc)}"}
def execute_sql(state: GraphState) -> GraphState:
    """Run the generated SQL safely and return a DataFrame."""
    db = DatabaseConnector(state["db_url"])
    try:
        df = db.execute_query(state["sql_query"])
        return {**state, "final_result": df, "error_message": ""}
    except Exception as exc:
        return {
            **state,
            "final_result":  None,
            "error_message": str(exc),
            "retry_count":   state.get("retry_count", 0) + 1,
        }

def generate_chart_spec(state: GraphState) -> GraphState:
    """Analyze DataFrame columns to pick the best chart type dynamically."""
    df = state.get("final_result")
    if df is None or len(df) < 2 or len(df.columns) < 2:
        return {**state, "chart_spec": None}

    # Extract column info
    col_info = []
    for c in df.columns:
        dtype = str(df[c].dtype)
        col_type = "number" if "int" in dtype or "float" in dtype else "category"
        if "datetime" in dtype:
            col_type = "datetime"
        col_info.append(f"{c} ({col_type})")

    api_key = os.environ.get("GROQ_API_KEY", "")
    client  = Groq(api_key=api_key)
    
    prompt = f"""
    Given the following dataframe columns, suggest the best Plotly chart type to visualize this data.
    Columns: {', '.join(col_info)}
    
    Output ONLY a valid JSON object with:
    "type": "bar", "line", "pie", or "scatter"
    "x": "column_name_for_x_axis"
    "y": "column_name_for_y_axis" (optional for pie)
    """

    try:
        response = client.chat.completions.create(
            model=CHART_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        chart_spec = json.loads(response.choices[0].message.content)
        return {**state, "chart_spec": chart_spec}
    except Exception:
        return {**state, "chart_spec": None}

# ── Build Graph for Generation (Pauses before execution) ──────────────────────
def test_sql_execution(state: GraphState) -> GraphState:
    """Validate SQL query syntax without running it (parses with SQLAlchemy)."""
    db = DatabaseConnector(state["db_url"])
    from sqlalchemy import text as sa_text
    try:
        with db.engine.connect() as conn:
            conn.execute(sa_text(f"EXPLAIN QUERY PLAN {state['sql_query']}"))
        return {**state, "error_message": ""}
    except Exception as exc:
        return {
            **state,
            "error_message": str(exc),
            "retry_count": state.get("retry_count", 0) + 1
        }

def build_generation_graph() -> StateGraph:
    """Graph to generate SQL and auto-correct (Step 1 of HITL)"""
    builder = StateGraph(GraphState)
    builder.add_node("extract_schema", extract_schema)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("generate_python", generate_python)
    builder.add_node("generate_sql",   generate_sql)
    builder.add_node("test_sql",       test_sql_execution)
    
    builder.set_entry_point("extract_schema")
    builder.add_edge("extract_schema", "classify_intent")
    
    def route_after_intent(state: GraphState):
        if state.get("is_python_task"):
            return "generate_python"
        return "generate_sql"
        
    builder.add_conditional_edges("classify_intent", route_after_intent)
    builder.add_edge("generate_python", END)
    builder.add_edge("generate_sql", "test_sql")
    
    def route_after_test(state: GraphState):
        if state.get("error_message") and state.get("retry_count", 0) < 3:
            return "generate_sql"
        return END
        
    builder.add_conditional_edges("test_sql", route_after_test)
    return builder.compile()

# ── Build Graph for Execution (Step 2 of HITL) ───────────────────────────────
def build_execution_graph() -> StateGraph:
    """Graph to execute SQL and generate chart specs"""
    builder = StateGraph(GraphState)
    builder.add_node("execute_python", execute_python)
    builder.add_node("execute_sql", execute_sql)
    builder.add_node("generate_chart", generate_chart_spec)
    
    # We dynamically set entry point in the helper below, or conditionally route
    # Let's route from a dummy start node if possible, or just build two graphs.
    # We'll handle routing dynamically by providing the exact start node in `invoke` 
    # but LangGraph doesn't allow dynamic entry points without a conditional router.
    
    # We'll use a router node:
    def route_exec(state: GraphState):
        if state.get("is_python_task"):
            return "execute_python"
        return "execute_sql"
    
    # LangGraph requires a single entry point, so we create a dummy node
    def init_exec(state: GraphState) -> GraphState: return state
    builder.add_node("init_exec", init_exec)
    builder.set_entry_point("init_exec")
    builder.add_conditional_edges("init_exec", route_exec)
    
    builder.add_edge("execute_python", END)
    
    def route_after_sql(state: GraphState):
        if state.get("error_message"):
            return END
        return "generate_chart"
        
    builder.add_conditional_edges("execute_sql", route_after_sql)
    builder.add_edge("generate_chart", END)
    return builder.compile()

# ── Public helpers ────────────────────────────────────────────────────────────
def run_generation(question: str, history: list[dict], db_url: str, data_dictionary: str = "") -> dict:
    """Generate SQL based on question and history."""
    graph = build_generation_graph()
    initial_state = {
        "db_url":          db_url,
        "data_dictionary": data_dictionary,
        "user_question":   question,
        "chat_history":    history,
        "database_schema": "",
        "is_python_task":  False,
        "python_code":     "",
        "sql_query":       "",
        "sql_explanation": "",
        "final_result":    None,
        "chart_spec":      None,
        "error_message":   "",
        "retry_count":     0,
    }
    result = graph.invoke(initial_state)
    return {
        "is_python_task":  result.get("is_python_task", False),
        "python_code":     result.get("python_code", ""),
        "sql_query":       result.get("sql_query", ""),
        "sql_explanation": result.get("sql_explanation", ""),
        "error_message":   result.get("error_message", ""),
    }

def run_execution(sql: str, db_url: str, is_python_task: bool = False, python_code: str = "") -> dict:
    """Execute SQL and generate charts."""
    graph = build_execution_graph()
    initial_state = {
        "db_url":          db_url,
        "data_dictionary": "",
        "user_question":   "",
        "chat_history":    [],
        "database_schema": "",
        "is_python_task":  is_python_task,
        "python_code":     python_code,
        "sql_query":       sql,
        "sql_explanation": "",
        "final_result":    None,
        "chart_spec":      None,
        "error_message":   "",
        "retry_count":     0,
    }
    result = graph.invoke(initial_state)
    return {
        "final_result":  result.get("final_result"),
        "chart_spec":    result.get("chart_spec"),
        "error_message": result.get("error_message", ""),
    }

def _df_to_text(df) -> str:
    """Convert a small DataFrame to text, with fallback if tabulate not installed."""
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return df.to_string(index=False)

def auto_explore_table(table_name: str, db_url: str) -> list[dict]:
    """Run 3-5 discovery queries on a newly uploaded table and return results with charts."""
    db = DatabaseConnector(db_url)
    schema = db.get_table_schema(table_name)

    # Get a sample of rows for context
    try:
        sample_df = db.execute_query(f"SELECT * FROM [{table_name}] LIMIT 5")
        sample_md = _df_to_text(sample_df)
    except Exception:
        sample_md = "(unavailable)"

    api_key = os.environ.get("GROQ_API_KEY", "")
    client = Groq(api_key=api_key)

    prompt = f"""
    You are an expert Data Analyst. Given this table schema and sample data, generate exactly 4 SQL exploration queries
    that would give a business user useful insights about their data. Include:
    - 1 row count / overview query
    - 1 aggregation query (GROUP BY on a categorical column)
    - 1 sorting/top-N query
    - 1 distribution or statistical summary query

    TABLE SCHEMA:
    {schema}

    SAMPLE DATA (first 5 rows):
    {sample_md}

    Rules:
    - Use proper SQLite syntax with bracket quoting: [table_name] or `table_name`
    - Use the real column names from the schema
    - Each query must be a SELECT statement
    - Keep queries simple (no subqueries, no CTEs)
    - Output ONLY valid JSON: {{"queries": [{{"question": "question text", "sql": "SELECT ..."}}]}}
    """

    try:
        response = client.chat.completions.create(
            model=CHART_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        queries = parsed.get("queries", [])[:4]
    except Exception as e:
        print(f"Error generating exploration queries: {e}")
        queries = [
            {"question": f"How many rows are in {table_name}?", "sql": f"SELECT COUNT(*) AS row_count FROM [{table_name}]"},
            {"question": f"Show all columns and first 10 rows of {table_name}", "sql": f"SELECT * FROM [{table_name}] LIMIT 10"},
        ]

    results = []
    for q in queries:
        sql = q.get("sql", "")
        question = q.get("question", "")
        try:
            df = db.execute_query(sql)
            if df is not None and len(df) > 0:
                results.append({
                    "question": question,
                    "sql": sql,
                    "df": df,
                    "error": None,
                })
            else:
                results.append({
                    "question": question,
                    "sql": sql,
                    "df": df,
                    "error": "Query returned no results" if df is not None else "Execution returned None",
                })
        except Exception as e:
            results.append({
                "question": question,
                "sql": sql,
                "df": None,
                "error": str(e),
            })

    return results


def auto_generate_dashboard(table_name: str, db_url: str) -> dict:
    """
    Generate a full auto-dashboard: KPI cards, charts, executive summary, and suggestions.
    Returns: {"title", "table_name", "kpis": [...], "charts": [...], "summary": "...", "suggested_questions": [...]}
    """
    db = DatabaseConnector(db_url)
    schema = db.get_table_schema(table_name)

    try:
        sample_df = db.execute_query(f"SELECT * FROM [{table_name}] LIMIT 5")
        sample_md = _df_to_text(sample_df)
    except Exception:
        sample_md = "(unavailable)"

    api_key = os.environ.get("GROQ_API_KEY", "")
    client = Groq(api_key=api_key)

    # Phase 1: Determine KPIs, chart layout, title, and suggested questions
    layout_prompt = f"""
    You are an expert BI Analyst designing a dashboard for a business user.

    TABLE SCHEMA:
    {schema}

    SAMPLE DATA (first 5 rows):
    {sample_md}

    Design a dashboard with:
    1. A **dashboard_title** — a short, professional business name (e.g. "Restaurant Sales Performance Dashboard").
    2. **3-4 KPI cards** — key metrics a business owner would care about most.
       For each KPI, provide an SQL query (SQLite syntax, bracket quoting), a label, and a format ("currency", "number", "percent", "integer").
    3. **2-3 charts** — the most insightful visualizations.
       For each chart, provide: title, SQL query, chart type ("bar", "line", "pie", "scatter"), x column, y column.
       Mark the most important chart with "is_main": true.
    4. **3 suggested_questions** — insightful follow-up questions a business user might ask next.

    Rules:
    - Use exact column names from the schema
    - Use bracket quoting: [{table_name}]
    - Keep SQL simple (GROUP BY, ORDER BY, LIMIT, aggregate functions)
    - Make KPIs diverse (count, sum, average, etc.)
    - suggested_questions should be specific to this dataset's columns

    Output ONLY valid JSON with this structure:
    {{
      "dashboard_title": "Restaurant Sales Analysis",
      "kpis": [
        {{
          "label": "Total Revenue",
          "sql": "SELECT SUM(price * quantity_sold) AS value FROM [{table_name}]",
          "format": "currency"
        }}
      ],
      "charts": [
        {{
          "title": "Sales by Category",
          "sql": "SELECT category, SUM(quantity_sold) AS total FROM [{table_name}] GROUP BY category ORDER BY total DESC",
          "type": "bar",
          "x": "category",
          "y": "total",
          "is_main": true
        }}
      ],
      "suggested_questions": [
        "Which category has the highest profit margin?",
        "How do sales trend over time?",
        "What is the average order value per category?"
      ]
    }}
    """

    dashboard = {
        "title": f"Dashboard: {table_name}",
        "table_name": table_name,
        "kpis": [],
        "charts": [],
        "summary": "",
        "suggested_questions": [],
        "error": None,
    }

    try:
        response = client.chat.completions.create(
            model=CHART_MODEL,
            messages=[{"role": "user", "content": layout_prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        layout = json.loads(response.choices[0].message.content)
        dashboard["title"] = layout.get("dashboard_title", f"Dashboard: {table_name}")
        dashboard["suggested_questions"] = layout.get("suggested_questions", [])[:3]
    except Exception as e:
        dashboard["error"] = f"Layout generation failed: {e}"
        return dashboard

    # Phase 2: Execute KPI queries
    kpis = []
    for kpi_def in layout.get("kpis", [])[:4]:
        try:
            df = db.execute_query(kpi_def["sql"])
            value = df.iloc[0, 0] if df is not None and len(df) > 0 else None
            value = round(float(value), 2) if value is not None else None
            kpis.append({
                "label": kpi_def.get("label", "Metric"),
                "value": value,
                "format": kpi_def.get("format", "number"),
            })
        except Exception as e:
            kpis.append({
                "label": kpi_def.get("label", "Metric"),
                "value": None,
                "format": kpi_def.get("format", "number"),
                "error": str(e),
            })
    dashboard["kpis"] = kpis

    # Phase 3: Execute chart queries
    charts = []
    for chart_def in layout.get("charts", [])[:3]:
        try:
            df = db.execute_query(chart_def["sql"])
            charts.append({
                "title": chart_def.get("title", "Chart"),
                "df": df,
                "type": chart_def.get("type", "bar"),
                "x": chart_def.get("x"),
                "y": chart_def.get("y"),
                "is_main": chart_def.get("is_main", False),
            })
        except Exception as e:
            charts.append({
                "title": chart_def.get("title", "Chart"),
                "df": None,
                "type": chart_def.get("type", "bar"),
                "x": chart_def.get("x"),
                "y": chart_def.get("y"),
                "is_main": chart_def.get("is_main", False),
                "error": str(e),
            })
    dashboard["charts"] = charts

    # Phase 4: Generate executive summary from actual data
    context_parts = [f"Dashboard for table: {table_name}"]
    for kpi in kpis:
        val_str = f"{kpi['value']}" if kpi['value'] is not None else "N/A"
        context_parts.append(f"- {kpi['label']}: {val_str}")

    for c in charts:
        df_c = c.get("df")
        if df_c is not None and len(df_c) > 0:
            context_parts.append(f"\nChart: {c['title']}\n{_df_to_text(df_c.head(10))}")

    context_str = "\n".join(context_parts)

    summary_prompt = f"""
    You are an expert Business Analyst. Given the following dashboard data, write a 2-3 paragraph executive summary.
    Highlight key trends, surprises, and actionable insights. Write in clear business language.

    DASHBOARD DATA:
    {context_str}

    Output ONLY the markdown summary text.
    """

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.4,
            max_tokens=800
        )
        dashboard["summary"] = response.choices[0].message.content.strip()
    except Exception as e:
        dashboard["summary"] = f"Summary generation failed: {e}"

    return dashboard


def generate_sample_questions(db_url: str) -> list[str]:
    """Dynamically generate 4 business sample questions based on the database schema."""
    db = DatabaseConnector(db_url)
    tables = db.get_tables()
    if not tables:
        return []
        
    # Get schema for the first 5 tables
    schema_lines = []
    for t in tables[:5]:
        schema_lines.append(db.get_table_schema(t))
    schema_str = "\n".join(schema_lines)

    api_key = os.environ.get("GROQ_API_KEY", "")
    client  = Groq(api_key=api_key)
    
    prompt = f"""
    You are an expert Data Analyst. Given the following database schema, generate exactly 4 diverse, interesting, and analytically useful questions a business user might ask about this data.
    
    CRITICAL: Use ONLY the actual table names and column names from the schema below. Do NOT invent tables or columns.
    
    SCHEMA:
    {schema_str}
    
    Generate questions that reference specific columns and tables from the schema.
    Example good question: "Show total sales per category" (if category and sales columns exist)
    Example bad question: "What is the survival rate of Titanic passengers?" (if no Titanic data)
    
    Output ONLY a valid JSON object with a single key "questions" containing a list of 4 string questions.
    """

    try:
        response = client.chat.completions.create(
            model=CHART_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        return parsed.get("questions", [])[:4]
    except Exception as e:
        print(f"Error generating sample questions: {e}")
        return []

# ── Phase 1: Voice & Reporting ───────────────────────────────────────────────


def generate_executive_summary(pinned_items: list[dict]) -> str:
    """Generate a cohesive Markdown summary of all pinned charts/data."""
    if not pinned_items:
        return "No data available for summary."
        
    api_key = os.environ.get("GROQ_API_KEY", "")
    client = Groq(api_key=api_key)
    
    # Format pinned items into context
    context_lines = []
    for idx, item in enumerate(pinned_items):
        context_lines.append(f"--- Chart {idx+1} ---")
        context_lines.append(f"Question/Topic: {item.get('question', '')}")
        df = item.get("df")
        if df is not None:
            # Add top 5 rows to save context
            context_lines.append(_df_to_text(df.head(5)))
        context_lines.append("\n")
        
    context_str = "\n".join(context_lines)
    
    prompt = f"""
    You are an expert Data Analyst and Executive Assistant.
    I am providing you with several tables of data representing various metrics from our database.
    
    Please write a 3-paragraph executive summary analyzing the key trends, insights, and takeaways across all this data.
    Do not just list the data; synthesize it into a cohesive business narrative.
    
    DATA PROVIDED:
    {context_str}
    
    Output ONLY the markdown text for the summary.
    """
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1024
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating summary."
