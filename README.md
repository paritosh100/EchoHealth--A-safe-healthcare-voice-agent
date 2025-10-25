# EchoHealth: A Safe Voice Companion for Reliable Medical Information

A voice-first medical information assistant powered by LiveKit and OpenAI Realtime. Provides reliable health information from MEDLINE documents with safety-first design.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=06192E)](https://react.dev/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-orange)](https://livekit.io/agents)
[![OpenAI](https://img.shields.io/badge/OpenAI-Realtime-412991?logo=openai&logoColor=white)](https://platform.openai.com/)

## Features

- **Voice-first interaction** via WebRTC (LiveKit)
- **RAG-powered responses** from MEDLINE documents only
- **Safety-first design** - no personal medical advice
- **Inline citations** with source references [S1], [S2]
- **Real-time voice** using OpenAI Realtime API

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- LiveKit Cloud project (API key/secret)
- OpenAI API key

### Environment Setup

1. **Backend** (`backend/.env`):
```ini
LIVEKIT_API_KEY=lkc_xxx
LIVEKIT_API_SECRET=xxx
OPENAI_API_KEY=sk-xxx
```

2. **Frontend** (`frontend/.env.local`):
```ini
VITE_LIVEKIT_URL=wss://your-project-id.livekit.cloud
```

### Installation & Run

```bash
# Backend setup
cd backend
python -m venv .venv
. .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r ..\requirements.txt
pip install openai numpy faiss-cpu pypdf
python ingest.py  # Build document index

# Start services (2 terminals)
python agent.py   # Terminal 1: LiveKit agent
python server.py  # Terminal 2: Token server (port 5001)

# Frontend (separate terminal)
cd ../frontend
npm install
npm run dev  # Opens http://localhost:5173
```

## Usage

1. Click "Open Health Assistant" and allow microphone access
2. Ask general health questions covered by MEDLINE docs
3. Receive voice responses with inline citations
4. Agent refuses personal medical advice and recommends healthcare professionals

## Project Structure

```
livekit_health_agent/
├── backend/
│   ├── agent.py      # LiveKit Agents worker
│   ├── api.py        # RAG tools (search + answer)
│   ├── ingest.py     # Build FAISS index
│   ├── prompts.py    # Health safety rules
│   └── server.py     # Token server
├── frontend/         # React UI
├── docs/             # MEDLINE HTML files
└── rag/              # Generated FAISS index
```

## Safety Features

- **No personal medical advice** - agent declines diagnosis requests
- **Document-only responses** - answers only from indexed MEDLINE content
- **Uncertainty handling** - states when information isn't available
- **Professional referral** - recommends consulting healthcare providers

## Troubleshooting

- **Token errors**: Ensure Flask server runs on port 5001
- **RAG errors**: Run `python ingest.py` after adding documents
- **Connection issues**: Verify LiveKit URL and API credentials
- **Missing deps**: Install `pip install openai numpy faiss-cpu pypdf`

## Notes

- Re-run `python ingest.py` when adding/updating documents in `docs/`
- Agent joins room `health-room` automatically
- Edit `backend/prompts.py` to customize responses