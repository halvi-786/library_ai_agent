# library_ai_agent
An intelligent AI library assistant that helps students find relevant academic books and learning resources based on their courses, subjects, topics, and learning requirements. The agent understands natural-language queries, recommends suitable resources, checks book availability, and assists students with reservations and waitlists

S# 📚 Library AI Agent

An intelligent university library assistant powered by **IBM watsonx** (Llama 3.3 70B) and **watsonx Orchestrate**.  
Students can search books, check availability, make reservations, and receive personalised AI-driven reading recommendations.

---

## Architecture

```
┌─────────────────────────────┐
│      Frontend (HTML/JS)     │  ← frontend/index.html
│  Catalog · Chat · Reserve   │
└────────────┬────────────────┘
             │ REST (localhost:5000)
┌────────────▼────────────────┐
│   Backend (Flask · Python)  │  ← backend/app.py
│  /api/books  /api/chat      │
│  /api/recommendations       │
└────────────┬────────────────┘
             │ HTTPS
┌────────────▼────────────────┐
│   IBM watsonx (LLM)         │
│  meta-llama/llama-3-3-70b   │
└─────────────────────────────┘

┌─────────────────────────────┐
│  watsonx Orchestrate Agent  │  ← agents/library-ai-agent.yaml
│  search · check · reserve   │
│  AI recommendations         │
└─────────────────────────────┘
```

---

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
# Server starts at http://localhost:5000
```

### 2. Frontend

Open `frontend/index.html` directly in a browser (no build step needed).

### 3. Deploy to watsonx Orchestrate

```bash
# Activate your environment first
orchestrate env activate <your-env-name>

# Then deploy tools + agent
python deploy.py
```

---

## Configuration

| Variable | Value |
|---|---|
| `WATSONX_URL` | `https://au-syd.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29` |
| `MODEL_ID` | `meta-llama/llama-3-3-70b-instruct` |
| `PROJECT_ID` | `addfe882-3b61-4b3b-ab5d-d1bf25cbb5dd` |
| `API_KEY` | Set in `backend/app.py` and `tools/library_tools.py` |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/books` | List all books (filter: `subject`, `available`) |
| GET | `/api/books/search?q=<query>` | Full-text search |
| GET | `/api/books/<id>` | Get single book |
| POST | `/api/books/<id>/reserve` | Reserve or join waitlist |
| POST | `/api/recommendations` | AI-powered recommendations |
| POST | `/api/chat` | Conversational AI chat |
| GET | `/api/subjects` | List all subjects |
| GET | `/api/stats` | Library statistics |

---

## watsonx Orchestrate Tools

| Tool | Description |
|---|---|
| `search_library_books` | Full-text catalog search |
| `check_book_availability` | Real-time copy count |
| `reserve_library_book` | Reserve or waitlist a book |
| `get_ai_book_recommendations` | watsonx LLM recommendations |

---

## Project Structure

```
library-ai-agent/
├── backend/
│   ├── app.py              # Flask REST API + watsonx integration
│   └── requirements.txt
├── frontend/
│   └── index.html          # Single-page UI (Catalog · Recommend · Chat · Reserve)
├── tools/
│   ├── library_tools.py    # watsonx Orchestrate tool definitions
│   └── requirements.txt
├── agents/
│   └── library-ai-agent.yaml   # Agent spec for Orchestrate
├── deploy.py               # One-shot deployment script
└── README.md
```
