# NovaWorks PeopleOps Copilot — Progress Checklist

> Re-sync note: If starting a new session, paste this file back in to restore context.
> Project: AI HR Copilot extending CB Nest (simulated, since no starter repo access)
> Stack: FastAPI backend, Next.js frontend (deferred), SQLite (dev) → Postgres (prod),
> FAISS/Qdrant(embedded) for vectors → ChromaDB (prod), Dell AI Gateway → OpenAI/Gemini (factory pattern)

## Key Confirmed Decisions
- [x] Auth: minimal JWT built from scratch (roles: EMPLOYEE, MANAGER, ADMIN)
- [x] Frontend: single unified `/ai-copilot` chat, no tabs, router picks agent silently (deferred until backend done)
- [x] Router endpoint (`/api/v1/chat/router`): implementing it (optional in doc, required for our UX)
- [x] Bonuses in scope: Human-in-the-Loop Confirmation, Tracing/Observability, Evaluation Dataset
- [x] "Recent AI Actions" panel: action-only scope for now (from HR Action Agent only)
- [x] Vector store: Qdrant (embedded mode, no server) now → ChromaDB in production; FAISS as fallback
- [x] Relational DB: SQLite now → PostgreSQL in production
- [x] LLM: Dell AI Gateway now → OpenAI/Gemini via factory pattern
- [x] Design decisions logged under `docs/ai_architecture.md` → "Design Decisions" section (own section, not folded into other categories)
- [x] Full assignment document received — no remaining ambiguity

## Build Steps

- [x] Step 1: Project skeleton + requirements.txt + .env setup
- [x] Step 2: FastAPI app boots (health check endpoint)
- [x] Step 3: Database connection (SQLAlchemy engine + session)
- [ ] Step 4: First model (Employee) + Alembic migration + verify table
- [ ] Step 5: Remaining models (departments, hr_policies, leave_requests,
      leave_balances, tickets, projects, employee_projects, skills,
      employee_skills, announcements, ai_audit_logs)
- [ ] Step 6: Seed data script
- [ ] Step 7: Minimal JWT auth (login endpoint, role field)
- [ ] Step 8: Policy RAG module (ingestion → embeddings → vector_store → policy_rag.py)
- [ ] Step 9: `/api/v1/chat/policy` endpoint
- [ ] Step 10: SQL Agent module + guardrails
- [ ] Step 11: `/api/v1/chat/sql` endpoint
- [ ] Step 12: HR Action Agent + api_tools + permissions
- [ ] Step 13: `/api/v1/chat/actions` endpoint
- [ ] Step 14: Router endpoint (`/api/v1/chat/router`)
- [ ] Step 15: Audit logging wired into all three endpoints (with redaction of secrets/PAN/bank/passwords)
- [ ] Step 16: Frontend (`/ai-copilot` page + components) — deferred until backend works
- [ ] Step 17: Documentation (`ai_architecture.md`, `ai_permissions_matrix.md`, `ai_eval_results.md`, README)
- [ ] Step 18: Evaluation dataset + run against built system

## Notes / Open Questions Log
(Add anything unresolved here as we go)
--------------------------------------------------



## Status: In Progress

## Completed
- [x] Project folder structure scaffolded
- [x] FastAPI entry point (`backend/app/main.py`)
- [x] Pydantic settings config (`backend/app/core/config.py`)
- [x] `requirements.txt` with core dependencies
- [x] `.env` placeholder file

## In Progress
- [ ] Database models (`backend/app/models/`)
- [ ] Database session setup (`backend/app/db/`)
- [ ] Alembic migrations (`backend/alembic/`)
