# DataNova — AI-Powered BI Platform

Autonomous business intelligence: upload data, ask questions in natural language, get instant dashboards and AI-generated insights.

---

## Architecture

```
User Query (Natural Language)
        │
        ▼
┌───────────────────┐
│  LangGraph Agent  │  ← Intent classification, SQL/Python routing
│  Orchestrator     │
└───────┬───────────┘
        │
    ┌───┴───┐
    │       │
    ▼       ▼
┌────────┐ ┌──────────┐
│  SQL   │ │  Python  │  ← AST-validated sandbox
│ Engine │ │  Sandbox │
└───┬────┘ └────┬─────┘
    │           │
    └───┬───────┘
        │
        ▼
┌───────────────────┐
│  Analytics Engine │  ← Plotly charts, KPIs, data quality
│                   │
│  Dashboard Gen.   │  ← Auto-generated zone grid layout
│                   │
│  AI Insight       │  ← Executive summaries, trends
│  Narration        │
└───────────────────┘
```

## Features

- **Natural Language Querying** — Ask questions in plain English, get SQL or Python
- **Auto Dashboards** — KPI cards, charts, data quality panel, executive summary
- **Dual Execution** — SQL for queries, Python sandbox for ML/forecasting (AST-validated)
- **Audit Log** — Full query history with timing and error tracking
- **Multi-Connection** — Save and switch between database connections
- **Data Profile** — Per-column stats, correlation heatmaps, histograms
- **Chat-to-Dashboard** — Create dashboards directly from chat results
- **Theme Toggle** — Dark/light mode with glassmorphic UI

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit, Plotly |
| AI/Orchestration | LangGraph, Groq (LLaMA) |
| Backend | SQLAlchemy, Pandas |
| Security | AST-based Python sandbox, SQL injection prevention |
| Deployment | Docker, Streamlit Cloud |

## Quick Start

```bash
# Clone
git clone https://github.com/Aryaajaiswal/DataNova.git
cd DataNova

# Install
pip install -r requirements.txt

# Set API key
echo "GROQ_API_KEY=gsk_..." > .env

# Run
streamlit run app.py
```

### Docker

```bash
docker compose up -d
```

## Live Demo

[https://datanova.streamlit.app](https://datanova.streamlit.app)

## License

MIT
