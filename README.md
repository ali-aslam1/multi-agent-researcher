# Multi-Agent Research Assistant 🌌

An autonomous AI Research Assistant built using **FastAPI**, **Next.js (React)**, **Groq LPU Inference**, and **LangGraph**. The system takes a single user research topic, dynamically breaks it down into sub-queries, delegates those queries to specialized sub-agents, and aggregates the results into a structured, responsive markdown report with inline citations and sources.

---

## Project Structure

```text
├── backend/                  # FastAPI Application
│   ├── venv/                 # Python Virtual Environment
│   ├── .env                  # API Key Config (.gitignore-ed)
│   ├── main.py               # FastAPI server & Groq SDK integration
│   └── requirements.txt      # Backend Python dependencies
│
├── frontend/                 # Next.js Application
│   ├── src/app/
│   │   ├── page.jsx          # UI dashboard & Markdown parser
│   │   ├── layout.jsx        # App layout metadata
│   │   └── globals.css       # Premium custom Vanilla CSS stylesheet
│   ├── package.json          # Frontend packages & fallback dev scripts
│   └── next.config.mjs       # Next.js ES module configuration
│
└── run.txt                   # Quick startup command checklist
```

---

## Quick Start Instructions

You will need two terminals open in the root folder of this project.

### 1. Configure API Keys
Before running, open `backend/.env` and replace the placeholder with your actual **Groq API Key**:
```env
GROQ_API_KEY=gsk_your_actual_key_here
```

### 2. Start the Backend API (Terminal 1)
```bash
# Navigate to backend
cd backend

# Activate your virtual environment
# For PowerShell:
.\venv\Scripts\Activate.ps1
# For CMD:
.\venv\Scripts\activate.bat

# Start FastAPI server
python main.py
```
*The API server will listen on [http://localhost:8000](http://localhost:8000).*

### 3. Start the Frontend Dashboard (Terminal 2)
```bash
# Navigate to frontend
cd frontend

# Install package dependencies
npm install

# Launch Next.js dev server
npm run dev
```
*The dashboard UI will boot up on [http://localhost:3000](http://localhost:3000).*

---

## Phase 1 Deliverables Achieved
- [x] **Venv Isolation**: Uncorrupted virtual environment configured under `backend/venv` storing dependencies natively.
- [x] **FastAPI Endpoint**: Exposed POST `/research` endpoint utilizing the official Groq SDK with type-safe schemas.
- [x] **Webpack Dev Fallback**: Custom Next.js script configurations bypassing platform SWC compile issues on Windows systems.
- [x] **Premium Glassmorphic Design**: Clean custom CSS using deep space gradients, reactive glowing layout focus states, spinning orchestrator loaders, and a responsive layout.
- [x] **Local Markdown Parser**: Seamlessly renders headings, lists, bold formatting, inline code block styling, and blockquotes for raw model output.
