# Multi-Agent Research Assistant

An autonomous AI research tool that accepts a natural language query, breaks it into sub-questions, searches the web, summarizes sources, audits contradictions, and compiles a final cited markdown report — all streamed live to the browser.

**Stack:** FastAPI · Next.js · LangGraph · Groq (llama-3.3-70b) · Tavily · Mojeek

---

## How It Works

The backend runs a 5-node LangGraph pipeline, streamed to the frontend via Server-Sent Events (SSE):

| Node | Role |
|---|---|
| **Orchestrator** | Decomposes the query into 2–3 focused sub-questions with optimized search terms |
| **Search Agent** | Queries Tavily API (primary) or scrapes Mojeek (fallback) for each sub-question |
| **Summarizer** | Sends each set of search results to Groq and generates a factual summary with citation |
| **Critic** | Analyzes all summaries for contradictions and conflicting facts across sources |
| **Aggregator** | Synthesizes everything into a single structured markdown report with inline citations |

The frontend tracks each pipeline stage in real time and renders the final report with a custom markdown parser.

---

## Project Structure

```
├── backend/
│   ├── agent_graph.py      # LangGraph graph: all 5 agent nodes + web search logic
│   ├── main.py             # FastAPI server, POST /research endpoint, SSE streaming
│   ├── test_graph.py       # Graph unit tests
│   ├── requirements.txt    # Python dependencies
│   └── .env                # API keys (gitignored)
│
└── frontend/
    └── src/app/
        ├── page.jsx        # UI dashboard, SSE consumer, pipeline tracker, markdown renderer
        ├── layout.jsx      # App layout & metadata
        └── globals.css     # Stylesheet
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com) — required
- A [Tavily API key](https://app.tavily.com) — optional but recommended (falls back to Mojeek scraping without it)

---

## Setup & Running

Two terminals are required — one for the backend, one for the frontend.

### Backend (Terminal 1)

Configure your API keys in `backend/.env`:
```env
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here
```

```bash
cd backend

# Activate virtual environment
# PowerShell:
.\venv\Scripts\Activate.ps1
# CMD:
.\venv\Scripts\activate.bat

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
python main.py
```

API runs at `http://localhost:8000` · Swagger docs at `http://localhost:8000/docs`

### Frontend (Terminal 2)

```bash
cd frontend
npm install       # first time only
npm run dev
```

Dashboard runs at `http://localhost:3000`

---

## Web Search Behavior

- **With `TAVILY_API_KEY` set:** Uses the Tavily Search API — structured, fast, AI-optimized results.
- **Without it:** Falls back to scraping [Mojeek](https://www.mojeek.com), a scraping-friendly search engine. Results may be less precise.

Setting the Tavily key is strongly recommended for best research quality.
