# NovaWorks PeopleOps Copilot — AI Permissions & Security Matrix

> Document Version: 1.0.0  
> System: NovaWorks HR Copilot  
> Scope: Role-Based Access Control (RBAC), Column Filtering, Action Privileges, & Human-in-the-Loop Policies  

---

## 1. Overview of System Roles

The NovaWorks HR Copilot enforces strict Multi-Tier Role-Based Access Control (RBAC) across all AI interfaces. The system defines three standard roles:

1. **`EMPLOYEE`**: Standard staff member. Has access to general policy RAG, personal HR data, self-service leave requests, and IT ticket submission.
2. **`MANAGER`**: Team supervisor. Has employee privileges plus team performance visibility, leave approval rights for direct reports, and project member assignment.
3. **`ADMIN`**: HR & Systems Administrator. Full operational access including company-wide announcements, system configuration, and ticket resolution.

---

## 2. Policy RAG Document Access Matrix

| Policy Document Category | Document Scope / Visibility | `EMPLOYEE` | `MANAGER` | `ADMIN` |
|---|---|:---:|:---:|:---:|
| **General HR Policies** | Annual Leave, Sick Leave, Code of Conduct, WFH Guidelines | ✅ Full | ✅ Full | ✅ Full |
| **Benefits & Insurance** | Health Coverage, Wellness Stipend, OPD Reimbursement | ✅ Full | ✅ Full | ✅ Full |
| **Managerial Guidelines** | Team Management, Performance Review Schedules | ❌ Blocked | ✅ Full | ✅ Full |
| **Executive & Legal** | Executive Compensation Policies, Legal Severance Terms | ❌ Blocked | ❌ Blocked | ✅ Full |

---

## 3. SQL Agent Query & Data Redaction Matrix

The SQL Agent enforces schema filtering, SQL query blocklists, and column-level redaction depending on the caller's role.

### A. Allowed Tables & Query Scopes

| Table Name | Scope / Filter | `EMPLOYEE` | `MANAGER` | `ADMIN` |
|---|---|:---:|:---:|:---:|
| `employees` | Basic Profile (Name, Job Title, Email, Dept) | ✅ Own + Public | ✅ Team + Public | ✅ All |
| `departments` | Department Details & Head Info | ✅ All | ✅ All | ✅ All |
| `projects` | Active & Upcoming Projects | ✅ Assigned | ✅ Team Projects | ✅ All |
| `skills` & `employee_skills` | Technical & Functional Skills | ✅ All | ✅ All | ✅ All |
| `leave_requests` | Leave History & Status | ✅ Own Only | ✅ Team Direct Reports | ✅ All |
| `tickets` | HR & IT Support Tickets | ✅ Own Only | ✅ Department Tickets | ✅ All |
| `ai_audit_logs` | Interaction & Audit Records | ❌ Blocked | ❌ Blocked | ✅ All |

### B. Sensitive Field Redaction Matrix

| Column / Attribute Name | Description | `EMPLOYEE` | `MANAGER` | `ADMIN` |
|---|---|:---:|:---:|:---:|
| `hashed_password` | Auth Passwords | ⛔ Always Blocked | ⛔ Always Blocked | ⛔ Always Blocked |
| `bank_account_number` | Bank Details | ⛔ Always Blocked | ⛔ Always Blocked | ⛔ Always Blocked |
| `pan_number` | Tax Identification | ⛔ Always Blocked | ⛔ Always Blocked | ⛔ Always Blocked |
| `current_salary_usd` | Compensation | ❌ Redacted | ❌ Redacted | ✅ Unredacted |
| `date_of_birth` | PII DOB | ❌ Redacted | ❌ Redacted | ✅ Unredacted |

---

## 4. HR Action Agent Privilege Matrix

All HR mutations are dispatched to REST API endpoints using the caller's JWT token.

| Action Operation | API Endpoint Triggered | `EMPLOYEE` | `MANAGER` | `ADMIN` | Expected Result if Denied |
|---|---|:---:|:---:|:---:|---|
| **Apply Leave** | `POST /api/v1/leaves/requests` | ✅ Allowed | ✅ Allowed | ✅ Allowed | N/A |
| **Create Ticket** | `POST /api/v1/tickets` | ✅ Allowed | ✅ Allowed | ✅ Allowed | N/A |
| **Approve Leave** | `PATCH /api/v1/leaves/requests/{id}` | ❌ Denied | ✅ (Team Only) | ✅ Allowed | `HTTP 403 Forbidden` / Status: `DENIED` |
| **Reject Leave** | `PATCH /api/v1/leaves/requests/{id}` | ❌ Denied | ✅ (Team Only) | ✅ Allowed | `HTTP 403 Forbidden` / Status: `DENIED` |
| **Assign Project** | `POST /api/v1/employees/{id}/projects` | ❌ Denied | ✅ (Team Only) | ✅ Allowed | `HTTP 403 Forbidden` / Status: `DENIED` |
| **Create Announcement** | `POST /api/v1/announcements` | ❌ Denied | ❌ Denied | ✅ Allowed | `HTTP 403 Forbidden` / Status: `DENIED` |
| **Deactivate Employee** | `PATCH /api/v1/employees/{id}` | ❌ Denied | ❌ Denied | ✅ Allowed | `HTTP 403 Forbidden` / Status: `DENIED` |

---

## 5. Human-in-the-Loop (HITL) Confirmation Policy

To prevent unintended modifications, high-impact HR operations require explicit Human-in-the-Loop user confirmation before execution.

```
       [User Intent: "Approve John's Leave"]
                       │
                       ▼
       [Action Agent Identifies High-Impact Action]
                       │
                       ▼
    ┌──────────────────────────────────────────────┐
    │ Requires Confirmation:                       │
    │ "Pending Casual Leave from John (May 6-7).  │
    │ Confirm approval? (Yes/No)"                 │
    └──────────────────────┬───────────────────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
           [User Confirms]     [User Cancels]
                 │                   │
                 ▼                   ▼
           [Execute API]       [Abort Action]
```

### Action Risk Classification & Confirmation Rules

| Risk Level | Action Operations | HITL Confirmation Required? | Trigger Behavior |
|---|---|:---:|---|
| **LOW** | Get Leave Balance, Search Skills, Submit Support Ticket, View Policies | ❌ No (Automated Execution) | Immediate API dispatch & output |
| **MEDIUM** | Submit Personal Leave Request | ❌ No (Direct Submission) | Dispatches leave request to approval queue |
| **HIGH** | Approve Leave, Reject Leave, Assign Employee to Project | ✅ **YES** | Prompts user for explicit confirmation before API invocation |
| **CRITICAL** | Publish Company Announcement, Deactivate Employee Account | ✅ **YES (Strict)** | Prompts user with full payload details for confirmation |
