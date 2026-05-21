# DataNova

🌐 **Live Demo:** [https://datanova.streamlit.app](https://datanova.streamlit.app)

AI-powered autonomous business intelligence platform. Upload data, ask questions in natural language, and get instant dashboards, insights, and executive summaries.

---

## Why DataNova

Traditional analytics tools require technical expertise to extract insights from data. DataNova makes business intelligence conversational, autonomous, and accessible through AI-driven analytics workflows.

## Architecture

```
User Query
   │
   ▼
┌───────────────────┐
│  LangGraph Agent  │  ← Intent classification, SQL/Python routing
│  Orchestrator     │
└───────┬───────────┘
   │         │
   ▼         ▼
┌────────┐ ┌──────────┐
│  SQL   │ │  Python  │  ← AST-validated sandbox
│ Engine │ │  Sandbox │
└───┬────┘ └────┬─────┘
   │           │
   └─────┬─────┘
         │
         ▼
┌───────────────────┐
│  Analytics Engine │  ← Plotly, KPIs, data quality
│                   │
│  Dashboard Gen.   │  ← Auto-generated zone grid
│                   │
│  AI Narration     │  ← Executive summaries, trends
└───────────────────┘
```

## Key Features

- ✅ **Natural Language to SQL** — Ask questions in plain English
- ✅ **Autonomous Dashboard Generation** — KPIs, charts, data quality, filters
- ✅ **AI Executive Summaries** — Narrative insights from your data
- ✅ **Dual Execution Engine** — SQL for queries, Python sandbox for ML/forecasting
- ✅ **Dynamic KPI Detection** — Automatic metric identification
- ✅ **Conversational Analytics** — Multi-turn chat with memory
- ✅ **Multi-Agent Workflow** — LangGraph-powered orchestration

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit, Plotly |
| AI/Orchestration | LangGraph, Groq (LLaMA) |
| Backend | SQLAlchemy, Pandas, NumPy |
| Security | AST-based Python sandbox, SQL injection prevention |
| Deployment | Docker, Streamlit Cloud |

## Quick Start

```bash
git clone https://github.com/Aryaajaiswal/DataNova.git
cd DataNova
pip install -r requirements.txt
echo "GROQ_API_KEY=gsk_..." > .env
streamlit run app.py
```

### Docker

```bash
docker compose up -d
```

## Challenges & Learnings

- Balancing autonomous dashboard generation with visual clarity
- Improving reliability of LLM-generated SQL through self-correction loops
- Designing schema-aware AI workflows for multi-table databases
- Implementing secure Python execution via AST validation
- Optimizing chart selection dynamically based on data cardinality

## Roadmap

- Conversational dashboard editing ("add forecasting", "compare weekdays")
- Real-time database integrations (PostgreSQL, MySQL)
- Multi-user collaboration with saved dashboards
- AI anomaly detection and alerting
- Forecasting engine with ARIMA/Prophet

## License

MIT
