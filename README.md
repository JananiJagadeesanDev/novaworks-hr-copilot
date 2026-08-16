# NovaWorks PeopleOps Copilot 🚀

> Enterprise-grade AI HR Assistant built with FastAPI, Vector RAG (Qdrant), SQL Agent Guardrails, and REST API Tool Calling.

---

## 📌 Project Overview

**NovaWorks PeopleOps Copilot** extends modern HRMS capabilities by introducing an intelligent, multi-agent AI system. Employees, managers, and admins can ask questions in natural language to query HR policies, inspect organizational database records, and execute administrative HR actions with strict authorization and data redaction.

### Key Features
- **Multi-Agent Intent Router**: Automatically classifies incoming queries (`policy_rag`, `sql_agent`, `action_agent`).
- **Grounded Policy RAG**: Qdrant vector database retrieval over company policies with source citations.
- **Read-Only SQL Agent**: Converts natural language to safe read-only SQL with regex blocklists (`DROP`, `DELETE`, `UPDATE` blocked) and column redaction (`hashed_password`, `current_salary_usd`, `bank_account_number`, `pan_number`).
- **HR Action Agent via REST APIs**: Dispatches mutations (apply leave, approve leave, create ticket, assign project, create announcement) strictly via backend REST endpoints using caller JWT tokens — **Zero direct DB writes**.
- **Audit Logging & Redaction**: Automatically sanitizes and logs all AI queries and actions to `ai_audit_logs`.
- **Role-Based Access Control (RBAC)**: Enforces `EMPLOYEE`, `MANAGER`, and `ADMIN` role privileges across all agents.

---

## 🛠️ Technology Stack

- **Backend Framework**: FastAPI (Python 3.10+)
- **ORM & Database**: SQLAlchemy 2.0, Alembic, SQLite (Dev) → PostgreSQL (Prod)
- **Vector Database**: Qdrant (Embedded mode under `qdrant_data/`)
- **Embeddings Model**: `BAAI/bge-small-en-v1.5` via SentenceTransformers
- **LLM Abstraction**: Factory pattern supporting Mock Provider, Dell AI Gateway, OpenAI, and Gemini
- **Authentication**: JWT Bearer Tokens (`python-jose`, `passlib`)
- **HTTP Client for Tools**: `httpx.ASGITransport` in-process API execution

---

## 📁 Repository Structure

```text
novaworks-hr-copilot/
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/v1/           # FastAPI REST & Chat endpoints
│   │   ├── core/             # Security, JWT, settings config
│   │   ├── db/               # SQLAlchemy engine & session setup
│   │   ├── models/           # DB Models (Employee, Leave, Ticket, Policy, Audit Log)
│   │   └── services/
│   │       ├── ai/           # Policy RAG, SQL Agent, Action Agent, Router, Vector Store
│   │       └── audit.py      # Standalone audit logger & PII redactor
│   ├── ingest_policies.py    # Policy document chunking & vector ingestion
│   ├── run_eval.py           # Automated evaluation runner script
│   └── seed.py               # Database initial seed script
├── docs/                     # Technical documentation suite
│   ├── ai_architecture.md    # Architecture diagrams, endpoint specs & design decisions
│   ├── ai_permissions_matrix.md # Role-based access control & HITL policies
│   └── ai_eval_results.md    # Evaluation suite results report
├── eval/
│   └── dataset.json          # Benchmark evaluation dataset (22+ test cases)
├── assignment_04_ai_hr_copilot.md # Assignment specifications
└── progress.md               # Implementation progress tracking
```

---

## 🚦 Quick Start Guide

### 1. Environment Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows (or source .venv/bin/activate on Linux/Mac)

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migration & Data Seeding

```bash
# Run database migrations
alembic upgrade head

# Seed initial database records (Employees, Departments, Projects, Leave Balances)
python seed.py

# Ingest HR policy markdown documents into vector database
python ingest_policies.py
```

### 3. Run FastAPI Application

```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Docs (Swagger UI): `http://127.0.0.1:8000/docs`
- Health check endpoint: `http://127.0.0.1:8000/health`

---

## 🤖 AI Endpoint Overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/chat/router` | `POST` | Main AI entry point. Classifies query and delegates to appropriate agent. |
| `/api/v1/chat/policy` | `POST` | Grounded HR Policy RAG endpoint with source citations. |
| `/api/v1/chat/sql` | `POST` | Natural language database query endpoint with read-only guardrails. |
| `/api/v1/chat/actions` | `POST` | HR Action Agent endpoint executing REST API calls on caller's behalf. |

---

## 📊 Evaluation & Benchmark Suite

Run the automated evaluation benchmark suite against all AI agents across `EMPLOYEE`, `MANAGER`, and `ADMIN` personas:

```bash
python backend/run_eval.py
```

Results are printed to terminal and exported to `docs/ai_eval_results.md`.

---

## 📚 Documentation Links

- [AI Architecture & Design Specifications](file:///e:/capstone/novaworks-hr-copilot/docs/ai_architecture.md)
- [AI Permissions & Security Matrix](file:///e:/capstone/novaworks-hr-copilot/docs/ai_permissions_matrix.md)
- [AI Evaluation Benchmark Results](file:///e:/capstone/novaworks-hr-copilot/docs/ai_eval_results.md)
