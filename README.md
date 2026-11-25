# MeetMind AI

> **Local-First, Agentic Multimodal Meeting Intelligence and Productivity Assistant**

MeetMind AI is an intelligent meeting assistant built with a local-first philosophy. It empowers teams and individuals to capture, transcribe, summarize, and extract actionable insights from multimodal meeting data—including audio, video, transcripts, and shared content—while keeping sensitive data secure and under user control.

---

## Vision & Core Objectives

- **Local-First Privacy & Control**: Retain data sovereignty with local storage, local processing options, and minimal external service dependencies.
- **Multimodal Intelligence**: Understand context across speech, slides, screen recordings, text transcripts, and visual cues.
- **Agentic Workflows**: Move beyond passive transcription to proactive assistance—generating task tracking, automated follow-ups, decision logs, and contextual summaries.
- **Extensible & Modular**: Designed with clean separation between API layers, core processing logic, persistent models, schemas, and pluggable interfaces.

---

## Architecture Direction

MeetMind AI follows a decoupled client-server architecture:

```text
meetmind-ai/
├── frontend/             # User interface (web/desktop application)
├── backend/              # Core API server and orchestration engine
│   ├── app/
│   │   ├── api/          # Modular API routes and versioning
│   │   ├── core/         # Core application configurations, settings, security
│   │   ├── database/     # Database sessions, connection management, migrations
│   │   ├── models/       # Database ORM models
│   │   ├── schemas/      # Pydantic schemas for request/response validation
│   │   └── main.py       # FastAPI application entry point
│   ├── tests/            # Automated test suite
│   └── requirements.txt  # Python backend dependencies
├── storage/              # Local data storage tiers
│   ├── uploads/          # Raw uploads and temporary file intake
│   ├── audio/            # Processed and stored audio streams
│   └── processed/        # Analyzed artifacts, transcripts, and reports
├── docs/                 # Documentation and architecture decision records
└── scripts/              # Utility, automation, and operational scripts
```

---

## Planned Technology Stack

- **Backend**: Python 3.12+ / FastAPI / Uvicorn / Pydantic
- **Frontend**: Modern web frontend framework (React / Next.js / TypeScript)
- **Database & Storage**: SQLite / PostgreSQL (local-first or embedded storage)
- **Intelligence & Processing**: Multimodal processing pipelines, local/hybrid AI models (Whisper, speech models, LLM agents)

---

## Getting Started (Backend)

### Prerequisites

- Python 3.12 or newer installed on your machine.

### Installation

Install required dependencies directly using `pip`:

```powershell
pip install -r backend/requirements.txt
```

### Running the Backend

From the project root directory, launch the FastAPI server:

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

### API Endpoints

- **Root Status**: `GET http://127.0.0.1:8000/`
- **Health Check**: `GET http://127.0.0.1:8000/health`
- **Interactive Documentation**: `GET http://127.0.0.1:8000/docs`
