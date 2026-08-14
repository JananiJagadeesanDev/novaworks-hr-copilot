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
- [x] Step 4: First model (Employee) + Alembic migration + verify table
- [x] Step 5: Remaining models (departments, hr_policies, leave_requests,
      leave_balances, tickets, projects, employee_projects, skills,
      employee_skills, announcements, ai_audit_logs)
- [x] Step 6: Seed data script
- [x] Step 7: Minimal JWT auth (login endpoint, role field)
- [x] Step 7b: HR REST CRUD APIs (required before Action Agent can tool-call them)
      → POST/PATCH /api/v1/leaves/requests
      → POST/PATCH /api/v1/tickets
      → POST /api/v1/announcements
      → POST /api/v1/employees/{id}/projects
- [ ] Step 7c: Missing DB models — job_history, onboarding_tasks
      (job_history referenced in SQL Agent recommended tables; onboarding_tasks in architecture diagram)
- [ ] Step 8: Policy RAG module (ingestion → embeddings → vector_store → policy_rag.py)
- [ ] Step 9: `/api/v1/chat/policy` endpoint
- [ ] Step 10: SQL Agent module + guardrails (sql_agent.py + sql_guardrails.py)
- [ ] Step 11: `/api/v1/chat/sql` endpoint
- [ ] Step 12: HR Action Agent + api_tools.py + permissions.py
- [ ] Step 12b: `audit.py` service — standalone AI audit writer with secret/PAN/bank redaction
- [ ] Step 13: `/api/v1/chat/actions` endpoint
- [ ] Step 14: Router endpoint (`/api/v1/chat/router`)
- [ ] Step 15: Wire audit logging into all three chat endpoints
- [ ] Step 16: Frontend (`/ai-copilot` page + components) — deferred until backend works
- [ ] Step 17: Documentation (`ai_architecture.md`, `ai_permissions_matrix.md`, `ai_eval_results.md`, README)
- [ ] Step 18: Evaluation dataset + run against built system

## Bonus Steps (in scope)
- [ ] Bonus A: Human-in-the-Loop confirmation for high-impact actions
      (approve leave, reject leave, assign to project, create announcement, deactivate employee)
- [ ] Bonus B: LangSmith / OpenTelemetry tracing for AI workflows
      (prompt inputs, model outputs, tool calls, latency, token usage, permission failures)
- [ ] Bonus C: Prompt injection defense — tests for malicious content inside policy documents
- [ ] Bonus D: Streaming chat responses (SSE or WebSockets) for better UX
## AWS Deployment Steps

- [ ] Step 19: Dockerise the backend (Dockerfile + .dockerignore)
- [ ] Step 20: Push Docker image to Amazon ECR (Elastic Container Registry)
- [ ] Step 21: Provision RDS PostgreSQL instance (swap DATABASE_URL from SQLite → RDS)
- [ ] Step 22: Run Alembic migrations against RDS (`alembic upgrade head`)
- [ ] Step 23: Deploy backend container to ECS Fargate (task definition + service)
- [ ] Step 24: Configure Application Load Balancer (ALB) + target group for ECS service
- [ ] Step 25: Store secrets in AWS Secrets Manager or Parameter Store (JWT_SECRET_KEY, OPENAI_API_KEY, DATABASE_URL)
- [ ] Step 26: Configure IAM roles (ECS task role with least-privilege access)
- [ ] Step 28: Deploy frontend to AWS Amplify or S3 + CloudFront (deferred until frontend is built)
- [ ] Step 29: Configure custom domain + HTTPS via ACM (AWS Certificate Manager)
- [ ] Step 30: Set up CloudWatch logging + alarms for ECS tasks and ALB
## Guardrails Reference (SQL Agent — must block these columns)
```
hashed_password, bank_account_number, bank_account_name, bank_branch,
bank_ifsc, pan_number, pan_name, pan_dob, date_of_birth,
current_salary_usd, profile_photo_path, profile_photo_mime
```
SQL statements to block: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
REPLACE, TRUNCATE, PRAGMA, ATTACH, DETACH

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
