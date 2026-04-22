# QueryMind — NL2SQL Agent System

An AI-powered Natural Language to SQL agent that converts plain English questions into accurate PostgreSQL queries, executes them, and returns human-readable answers — with autonomous self-correction and full observability.

Built with **LangGraph** for agentic orchestration, **Groq** (Llama 3.3 70B) for LLM inference, and **pgvector** for semantic schema retrieval.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Natural Language Queries** | Ask questions in plain English — the agent writes, validates, and executes SQL for you |
| 🔄 **Self-Correction Loop** | If SQL fails, the agent automatically corrects and retries up to 3 times |
| 🛡️ **SQL Safety Validator** | Blocks dangerous DDL/DML (DROP, DELETE, UPDATE, etc.) before execution |
| 📊 **Observability Dashboard** | Real-time metrics, query history, and execution trace replay |
| 🔍 **Semantic Schema Retrieval** | Uses pgvector embeddings to find relevant tables/columns for each question |
| 📈 **Analytics API** | Success rates, latency tracking, daily stats, and failure analysis |
| ⚡ **95% Benchmark Accuracy** | Tested against 20 real-world business queries with ~3s avg latency |

---

## 🏗️ Architecture

```mermaid
graph LR
    A[User Question] --> B[Schema Retriever]
    B --> C[SQL Generator]
    C --> D[SQL Validator]
    D -->|Valid| E[SQL Executor]
    D -->|Invalid| F[SQL Corrector]
    E -->|Success| G[Result Formatter]
    E -->|Error| F
    F -->|Retry ≤ 3| D
    F -->|Retry > 3| H[Failure Handler]
    G --> I[Query Logger]
    H --> I
    I --> J[API Response]
```

**8-Node LangGraph Pipeline:**
1. **Schema Retriever** — Vector search for relevant schema context via pgvector
2. **SQL Generator** — LLM generates PostgreSQL query using Groq API
3. **SQL Validator** — Syntax check (sqlglot) + safety check + table existence
4. **SQL Executor** — Runs validated SQL against PostgreSQL
5. **SQL Corrector** — LLM fixes broken SQL with error context (retry loop)
6. **Failure Handler** — Graceful termination after max retries
7. **Result Formatter** — LLM converts raw data to natural language answer
8. **Query Logger** — Persists full execution trace for analytics

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, Recharts, SWR |
| **Backend** | Python 3.12, FastAPI, LangGraph, Groq SDK |
| **Database** | PostgreSQL 15 + pgvector |
| **LLM** | Llama 3.3 70B Versatile (via Groq) |
| **Embeddings** | all-MiniLM-L6-v2 (SentenceTransformers) |
| **Deployment** | Vercel (Frontend) + Render (Backend + Database) |

---

## 📁 Project Structure

```
QUERY-MIND/
├── backend/
│   ├── agents/
│   │   ├── graph.py          # LangGraph StateGraph definition
│   │   ├── nodes.py          # All 8 pipeline nodes
│   │   └── state.py          # QueryState TypedDict
│   ├── api/
│   │   ├── query.py          # POST /query endpoint
│   │   ├── analytics.py      # GET /analytics/* endpoints
│   │   └── embeddings.py     # POST /embeddings/rebuild
│   ├── db/
│   │   ├── connection.py     # asyncpg pool management
│   │   ├── init.sql          # pgvector extension setup
│   │   └── seed.py           # Schema embedding generation
│   ├── config.py             # Environment configuration
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Backend container
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # Query interface
│   │   │   ├── dashboard/page.tsx # Observability dashboard
│   │   │   ├── failures/page.tsx  # Failed queries view
│   │   │   ├── layout.tsx        # Root layout with sidebar
│   │   │   └── globals.css       # Design system
│   │   ├── components/
│   │   │   ├── QueryInput.tsx    # Search input component
│   │   │   ├── ResultTable.tsx   # Data table component
│   │   │   ├── SqlBlock.tsx      # SQL syntax display
│   │   │   ├── MetricCard.tsx    # Metric badge component
│   │   │   ├── TraceViewer.tsx   # Execution trace replay
│   │   │   ├── Sidebar.tsx       # Navigation sidebar
│   │   │   ├── SlideOver.tsx     # Slide-over panel
│   │   │   └── charts/          # Recharts components
│   │   └── lib/
│   │       ├── api.ts           # API client functions
│   │       └── types.ts         # TypeScript interfaces
│   ├── package.json
│   └── next.config.ts
├── tests/
│   ├── unit/                    # 29 unit tests
│   ├── integration/             # 16 integration tests
│   └── benchmark/               # 20-query accuracy benchmark
├── Dataset/                     # Olist e-commerce CSV files
├── render.yaml                  # Render deployment blueprint
├── docker-compose.yml           # Local development (PostgreSQL)
├── .env.example                 # Environment template
└── README.md
```

---

## 🚀 Deployment Guide

### Option A: Deploy to Cloud (Recommended)

#### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: QueryMind NL2SQL Agent"
git remote add origin https://github.com/YOUR_USERNAME/query-mind.git
git push -u origin main
```

#### Step 2: Deploy Backend to Render

1. Go to [render.com](https://render.com) and sign up (free)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml` and create:
   - A **PostgreSQL** database (free tier)
   - A **Web Service** for the FastAPI backend
5. After deployment, go to your backend service → **Environment** tab
6. Set `GROQ_API_KEY` to your Groq API key (get one free at [console.groq.com](https://console.groq.com))
7. Copy your backend URL (e.g. `https://querymind-backend.onrender.com`)

#### Step 3: Seed the Database

After Render deploys, you need to populate the database with the Olist dataset and schema embeddings. Connect to your Render PostgreSQL and run the seed scripts:

```bash
# Option 1: Use Render Shell (Dashboard → Web Service → Shell)
python -c "import asyncio; from db.seed import main; asyncio.run(main())"

# Option 2: Hit the API endpoint after deployment
curl -X POST https://YOUR-BACKEND-URL.onrender.com/embeddings/rebuild
```

#### Step 4: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign up (free)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Configure the project:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
5. Add Environment Variable:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://YOUR-BACKEND-URL.onrender.com` (from Step 2)
6. Click **Deploy**

#### Step 5: Verify

- Open your Vercel URL → Ask a question → Should get an AI-generated answer
- Visit `/dashboard` → Should see real-time metrics
- Visit `/failures` → Should show any failed queries

---

### Option B: Local Development

#### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker (for PostgreSQL only)

#### Step 1: Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/query-mind.git
cd query-mind
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

#### Step 2: Start PostgreSQL

```bash
docker-compose up -d postgres
```

#### Step 3: Setup Backend

```bash
cd backend
python -m venv ../venv
..\venv\Scripts\activate    # Windows
# source ../venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

#### Step 4: Seed Database

```bash
# From backend/ directory with venv activated
python -c "import asyncio; from db.seed import main; asyncio.run(main())"
```

#### Step 5: Start Backend

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### Step 6: Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📡 API Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query` | Submit a natural language question |
| `GET` | `/health` | Health check |
| `GET` | `/analytics/summary` | Aggregate metrics (total queries, success rate, etc.) |
| `GET` | `/analytics/history?limit=50` | Recent query log entries |
| `GET` | `/analytics/failures?limit=50` | Failed queries only |
| `GET` | `/analytics/slow-queries?threshold_ms=2000` | Queries above latency threshold |
| `GET` | `/analytics/trace/{query_id}` | Full execution trace for a specific query |
| `GET` | `/analytics/daily-stats` | Per-day aggregated statistics |
| `GET` | `/analytics/queries-per-day?days=7` | Queries per day for charts |
| `POST` | `/embeddings/rebuild` | Regenerate schema embeddings |

### Example Query

```bash
curl -X POST http://localhost:8000/query?include_trace=true \
  -H "Content-Type: application/json" \
  -d '{"question": "How many customers are there?"}'
```

**Response:**
```json
{
  "answer": "There are 99,441 customers in the database.",
  "sql": "SELECT COUNT(*) AS total_customers FROM olist_customers",
  "rows": [{"total_customers": 99441}],
  "metrics": {
    "retries": 0,
    "latency_ms": 2345.67,
    "success": true
  },
  "error": null,
  "trace_steps": [...]
}
```

---

## 📊 Benchmark Results

| Metric | Value |
|--------|-------|
| **Pass Rate** | 95% (19/20 queries) |
| **Avg Latency** | ~3,100ms |
| **Avg Retries** | 0.15 |
| **Total Time** | 81.5s for 20 queries |

Tested across 5 categories: Simple SELECT, GROUP BY/Aggregation, JOIN, Date Filtering, and Multi-Join queries.

---

## 🧪 Testing

```bash
# Unit Tests (29 tests)
venv\Scripts\pytest tests/unit/ -v

# Integration Tests (16 tests — requires running backend)
venv\Scripts\pytest tests/integration/ -v

# Benchmark (20 queries — requires running backend)
venv\Scripts\python tests/benchmark/benchmark_queries.py
```

---

## 🔮 Future Improvements

- [ ] Add authentication and rate limiting
- [ ] Support multiple database connections
- [ ] Add query caching layer (Redis)
- [ ] Implement streaming responses for long-running queries
- [ ] Add chart auto-generation from query results
- [ ] Support for more SQL dialects (MySQL, SQLite)

---

## 📄 License

MIT License — feel free to use this project for learning, portfolios, or production.
