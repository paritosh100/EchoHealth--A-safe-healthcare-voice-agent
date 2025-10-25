EchoHealth: A Safe Voice Companion for Reliable Medical Information

Overview
- Voice-first assistant using LiveKit and OpenAI Realtime
- Answers only from MEDLINE documents in `docs/`
- Inline citations like [S1], [S2]; refuses medical advice; plain language

Project structure
```
livekit_health_agent/
  backend/
    agent.py         # LiveKit Agents worker
    api.py           # RAG tools (MEDLINE search + grounded answer)
    ingest.py        # Build FAISS index from docs/
    prompts.py       # Health-specific rules and welcome message
    server.py        # Flask token server (/getToken)
  frontend/
    src/             # React (Vite) UI
  docs/              # MEDLINE HTML files
  rag/               # Generated FAISS index + metadata
  requirements.txt   # Backend dependencies
```

Prerequisites
- Python 3.10+
- Node.js 18+
- LiveKit Cloud project (API key/secret)
- OpenAI API key

Environment
1) `backend/.env`
```
LIVEKIT_API_KEY=lkc_xxx
LIVEKIT_API_SECRET=xxx
OPENAI_API_KEY=sk-xxx
```
2) `frontend/.env.local`
```
VITE_LIVEKIT_URL=wss://your-project-id.livekit.cloud
```

Setup
```
# Backend
cd backend
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
python ingest.py
python agent.py      # window 1
python server.py     # window 2 (serves http://localhost:5001)

# Frontend (in a separate terminal)
cd ../frontend
npm install
npm run dev          # opens http://localhost:5173
```

Usage
- Click “Open EchoHealth Assistant”, enter your name, allow microphone.
- Ask general questions covered by MEDLINE docs (e.g., "What is asthma?")
- You’ll hear answers with inline citations [S1], [S2].

Safety rules (enforced)
- No personal medical advice or treatment recommendations.
- If asked for diagnosis or personal guidance, EchoHealth declines and recommends consulting a qualified healthcare professional.
- If information isn’t found, it states uncertainty and offers to connect you with a specialist.

Notes
- Frontend requests tokens with `room=health-room`, which the agent also joins.
- Re-run `python ingest.py` if you add or change files in `docs/`.
# Optum Voice Agent (LiveKit + OpenAI RAG)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=06192E)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-orange)](https://livekit.io/agents)
[![OpenAI](https://img.shields.io/badge/OpenAI-Realtime-412991?logo=openai&logoColor=white)](https://platform.openai.com/)

A full‑stack, voice‑first assistant that connects users to a real‑time AI agent over LiveKit. The agent only answers from your indexed documents (RAG) and speaks back using OpenAI Realtime voice.

- Live voice via WebRTC (LiveKit)
- RAG over PDFs and text in `docs/`
- Multimodal agent with OpenAI Realtime voice
- Minimal React UI with built‑in transcription stream

---

## Contents
- Overview
- Architecture
- Repository structure
- Prerequisites
- Environment variables
- Setup & Run (Backend and Frontend)
- Indexing documents (RAG)
- How it works (key files)
- Common issues & troubleshooting

---

## Overview
- The frontend opens a modal, fetches a LiveKit access token from the backend, and joins a room.
- A Python worker (LiveKit Agents) connects to the same room and runs a multimodal agent powered by OpenAI Realtime.
- The agent is constrained to answer only from your indexed docs.

## Architecture
```
[User Browser]
   └─ React + LiveKit Components
        ├─ GET /api/getToken  ─────────▶  [Flask Backend]
        │                                 └─ Issues JWT using LIVEKIT_API_* via LiveKit API
        └─ Join LiveKit Room (VITE_LIVEKIT_URL)

[LiveKit Cloud/Server]
   └─ Routes audio/text between participants (browser ↔ agent worker)

[Python Worker (LiveKit Agents)]
   ├─ OpenAI Realtime voice model
   ├─ RAG tools (doc_search, doc_answer)
   └─ Answers strictly from `rag/` index built from `docs/`
```

## Repository structure
```
livekit_agent/
  backend/
    agent.py        # LiveKit Agents worker (OpenAI Realtime + RAG tools)
    api.py          # RAG tools (doc_search/doc_answer)
    server.py       # Flask token server (/getToken)
    ingest.py       # Build FAISS index from docs/
    prompts.py      # System prompts and welcome message
    db_driver.py    # (placeholder)
  frontend/
    src/            # React app (Vite)
  docs/             # Place your PDFs/text here for indexing
  rag/              # Generated FAISS index + metadata
  requirements.txt  # Backend core deps (install extras below for RAG)
```

## Prerequisites
- Python 3.10+
- Node.js 18+
- A LiveKit Cloud project (or self‑hosted LiveKit) with API key/secret
- An OpenAI API key (for embeddings + Realtime voice)
- Windows/macOS/Linux (author environment: Windows 10)

## Environment variables
Create two `.env` files:

1) `backend/.env`
```ini
LIVEKIT_API_KEY=lkc_xxx
LIVEKIT_API_SECRET=xxx
OPENAI_API_KEY=sk-xxx
```

2) `frontend/.env.local`
```ini
VITE_LIVEKIT_URL=wss://your-project-id.livekit.cloud
```

Notes:
- The backend loads `.env` from its working directory. Run backend commands from `backend/`.
- The frontend reads `VITE_*` variables from `frontend/.env*`.

## Setup & Run

### 1) Backend (Flask token server + Agent worker)
Run all backend commands from the `backend/` directory so relative paths resolve correctly.

```powershell
# From project root
cd backend

# Create and activate venv (Windows PowerShell)
python -m venv .venv
. .venv\Scripts\Activate.ps1

# Install core deps
pip install -r ..\requirements.txt

# Install RAG + utilities (ingestion uses these)
pip install openai numpy faiss-cpu pypdf

# Build the document index (see section below)
python ingest.py

# Start the LiveKit Agents worker (OpenAI Realtime)
python agent.py

# In a separate terminal, start the Flask token server (port 5001)
python server.py
```

### 2) Frontend (React + Vite)
```bash
# From project root
cd frontend
npm install

# Dev server
npm run dev
```

#### Dev proxy for token endpoint
The frontend fetches `/api/getToken`, while Flask serves `/getToken` on `http://localhost:5001`.
Add a dev proxy to `frontend/vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, '')
      }
    }
  }
})
```

## Indexing documents (RAG)
- Place PDFs and text files in `docs/`.
- From `backend/`, run: `python ingest.py`.
- The script writes `rag/faiss.index` and `rag/meta.pkl`.
- On startup, the agent will refuse to answer if the index is missing.

## How it works (key files)
- `backend/agent.py`: Boots a `MultimodalAgent` with OpenAI Realtime voice ("shimmer"), subscribes to the room, streams speech, and responds.
- `backend/api.py`: Implements two AI‑callable tools:
  - `doc_search(query, k)`: finds similar chunks in the FAISS index
  - `doc_answer(query)`: returns a compact, grounded answer or refuses
- `backend/server.py`: Issues LiveKit JWTs using `LIVEKIT_API_KEY/SECRET`.
- `frontend/src/components/LiveKitModal.jsx`: Fetches token, joins room, renders assistant UI.

## Common issues & troubleshooting
- Token request 404/500
  - Ensure Vite dev proxy is configured to forward `/api` → `http://localhost:5001` with rewrite.
  - Flask server must be running (`python server.py`).
- RAG error: "RAG index missing. Run `python ingest.py`."
  - Add files to `docs/` and run `python ingest.py` from `backend/` after setting `OPENAI_API_KEY`.
- LiveKit connection failure
  - Verify `VITE_LIVEKIT_URL` (must be a `wss://` LiveKit URL) and your project has an active room.
- 401 Unauthorized joining room
  - Check `LIVEKIT_API_KEY/SECRET` in `backend/.env` and that the token server is reachable via `/api/getToken`.
- No audio or mic permissions
  - Allow microphone access in the browser; ensure you joined the room.
- Missing Python deps (ingestion)
  - Install extras: `pip install openai numpy faiss-cpu pypdf`.

## Notes
- By design, the agent answers only from your indexed documents and will refuse otherwise.
- Edit `backend/prompts.py` to change the persona or response style.

## Acknowledgements
- [LiveKit Agents](https://livekit.io/agents)
- [LiveKit Components](https://livekit.io/docs/client/components)
- [OpenAI Realtime](https://platform.openai.com/docs/guides/realtime)
