# Legalbandu — From Handshake to Contract

[![Tests](https://img.shields.io/badge/pytest-8%20passed-emerald)](https://github.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-blue)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB)](https://react.dev)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20%26%20Postgres-3ECF8E)](https://supabase.com)
[![License](https://img.shields.io/badge/license-MIT-slate)](LICENSE)

> **Legalbandu** is an AI-powered full-stack platform that transforms informal business conversations (WhatsApp chats, voice notes, emails) into clear, mutually reviewed, confirmed, and version-controlled legal agreements.

---

## 1. Product Vision & Positioning

People frequently make business agreements informally through WhatsApp messages, emails, and verbal conversations. These informal exchanges frequently leave critical terms underspecified—prices, payment milestones, completion deadlines, responsibilities, and subsequent change requests.

**Legalbandu** bridges the gap between everyday business communication and legal certainty:
- **Deal Rooms:** Create private workspaces for business transactions.
- **Secure Invitations:** Cryptographically hashed single-use tokens bind counterparties.
- **Conversation & Call Recording Import:** Ingest raw chat transcripts, exported `.txt` files, or phone call voice recordings (`.mp3`, `.wav`, `.m4a`, `.webm`, `.ogg`) with in-browser mic capture.
- **Call-to-Agreement AI Pipeline:** Automatically transcribes audio dialogue, extracts core commercial key points (scope, price, schedule, acceptance criteria), and drafts an official `AgreementVersion`.
- **Legal Bond Upload & Multi-Vector AI Detector:** Upload legal bonds, indemnity deeds, and e-stamps (`.pdf`, `.docx`, `.txt`, image OCR). Scans for ChatGPT/synthetic LLM text with immediate warning alerts and 1-click plain-language agreement conversion.
- **AI Term Extraction:** Google Gemini analyzes conversations, flagging confirmed terms, ambiguities, and contradictions.
- **Missing-Term Clarification:** Structured resolution of missing terms and questions.
- **Plain-Language Agreement Generation:** Automatic drafting of clear, structured bilateral contracts.
- **Bilateral Review & Approval:** Mutually confirmed only when **both** parties approve the identical version.
- **Amendment Management:** Side-by-side tracking of changes (e.g., price and deadline revisions). Any substantive change invalidates prior approvals and increments the version number.
- **Tamper-Evident SHA-256 Audit Chain:** Cryptographically linked activity history with real-time verification.
- **ReportLab PDF Export:** Formatted legal documents with participant verification stamps and statutory disclaimers.

> **Legal Disclaimer:** Legalbandu assists with organizing and documenting agreements. It does not replace qualified legal counsel or guarantee statutory enforceability in specific jurisdictions.

---

## 2. Technology Stack

- **Frontend:** React 18, Vite, JavaScript, Tailwind CSS, Lucide Icons, `@supabase/supabase-js`, React Router.
- **Backend:** Python 3.13, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2.
- **Database & Auth:** Supabase PostgreSQL with Row Level Security (RLS) policies; local SQLite fallback for offline development.
- **AI Engine:** Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`).
- **PDF Generation:** ReportLab Platypus engine.
- **Testing:** Pytest with automated integration test suite.
- **Hosting Targets:** Vercel (Frontend), Render (Backend), Supabase (Database & Auth).

---

## 3. Strict No-Dummy-Data Policy

Legalbandu strictly adheres to an authentic business data policy:
- Zero pre-populated sample deals or fake customer profiles.
- Zero simulated metrics or placeholder charts.
- Honest empty states: When an account is new, deal counts are strictly `0`, with clear calls-to-action to create real deals.
- Honest AI fallback: When `GEMINI_API_KEY` is not configured, a clear diagnostic message is displayed, and full manual deal-term entry is provided.

---

## 4. Repository Structure

```
legalbandu/
├── frontend/
│   ├── src/
│   │   ├── components/       # Navbar, AuthModal, NewDealModal, InviteModal, ProfileModal, Notifications
│   │   ├── context/          # AuthContext (Supabase Auth & session handling)
│   │   ├── pages/            # LandingPage, DashboardPage, DealWorkspacePage, InvitePage
│   │   ├── services/         # api.js (REST client), supabase.js (SDK initialization)
│   │   ├── App.jsx           # Application routing and global modals
│   │   ├── main.jsx          # React DOM entry point
│   │   └── index.css         # Tailwind directives & typography
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env.example
│   └── .env
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point, CORS & lifecycle
│   │   ├── config.py         # Pydantic Settings
│   │   ├── auth.py           # Supabase JWT verification & IDOR authorization
│   │   ├── database.py       # Engine, session factory & table initialization
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── services/         # audit_service, ai_service, pdf_service, notification_service
│   │   └── routers/          # health, auth, deals, invitations, conversations, clarifications, agreements, amendments, activity, notifications
│   ├── tests/                # Automated pytest workflow suite
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql  # Complete PostgreSQL tables, indexes & triggers
│       └── 002_rls_policies.sql    # Comprehensive Row Level Security policies
└── README.md
```

---

## 5. Database Schema & Row Level Security

The complete SQL migrations are located in `supabase/migrations/`:
1. `001_initial_schema.sql`:
   - `profiles`: User information linked to `auth.users`.
   - `deals`: Core deal metadata, status, and currency.
   - `deal_participants`: Roles (`creator`, `counterparty`), invitation token hashes, and expiration.
   - `conversations` & `messages`: Raw content and parsed speaker bubbles.
   - `deal_analyses`: Structured JSON outputs from Gemini AI.
   - `clarification_answers`: Answers to ambiguities with author attribution.
   - `agreement_versions`: Version-controlled document content with unique `(deal_id, version_number)`.
   - `agreement_approvals`: Bilateral confirmation records (`approved`, `changes_requested`).
   - `agreement_comments`: Clause-level commentary.
   - `amendments`: Side-by-side tracking of proposed changes.
   - `activity_logs`: Tamper-evident SHA-256 hash-chained audit events.
   - `notifications`: In-app notification queue.

2. `002_rls_policies.sql`:
   - Enforces isolation: Users can access only deals they participate in.
   - Approvals can be submitted only by the authenticated participant.
   - Audit logs are append-only (no update/delete permissions).

---

## 6. Quickstart: Local Development

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- Git

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env

# Run automated tests
python -m pytest tests -v

# Start the FastAPI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API is now running at `http://127.0.0.1:8000`. You can inspect documentation at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup
In a new terminal:
```bash
cd frontend

# Install dependencies
npm install

# Create .env from template
cp .env.example .env

# Start Vite dev server
npm run dev -- --host 127.0.0.1 --port 5173
```
Open `http://127.0.0.1:5173/` in your browser.

---

## 7. Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `SUPABASE_URL` | Supabase Project URL | `https://xyz.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Service Role Secret | `eyJhb...` |
| `SUPABASE_JWT_SECRET` | Supabase JWT Secret for token verification | `your-jwt-secret` |
| `DATABASE_URL` | Direct PostgreSQL connection string | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `FRONTEND_URL` | Frontend origin for CORS | `http://localhost:5173` |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed conversation upload size | `10` |

### Frontend (`frontend/.env`)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Backend API base URL | `http://127.0.0.1:8000/api` |
| `VITE_SUPABASE_URL` | Supabase Project URL | `https://xyz.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Supabase Public Anonymous Key | `eyJhb...` |

---

## 8. Automated Testing

The automated test suite verifies all critical business rules:
```bash
cd backend
venv\Scripts\python -m pytest tests -v
```

Tests validate:
1. `test_health_and_empty_dashboard`: Zero fabricated data, honest empty dashboard.
2. `test_deal_creation_and_invitation_acceptance`: Single-use invitation token hashing, counterparty acceptance, 403 authorization enforcement against unauthorized users.
3. `test_conversation_import`: Multi-speaker message parsing and timestamp preservation.
4. `test_clarification_submission`: Attributed Q&A for missing terms.
5. `test_agreement_versioning_and_mutual_approval`: Two-party approval rule for mutual confirmation.
6. `test_approval_reset_on_amendment_edit`: Version incrementing (v1 → v2) and approval invalidation.
7. `test_pdf_generation`: ReportLab PDF byte generation with formatting.
8. `test_tamper_evident_audit_chain`: Cryptographic SHA-256 hash chaining and sequence verification.

---

## 9. Production Deployment Guide

### Deploy Database & Auth (Supabase)
1. Create a new project at [supabase.com](https://supabase.com).
2. In the Supabase Dashboard, go to **SQL Editor** and execute:
   - `supabase/migrations/001_initial_schema.sql`
   - `supabase/migrations/002_rls_policies.sql`
3. Under **Authentication -> URL Configuration**, set **Site URL** to your production frontend URL (e.g. `https://legalbandu.vercel.app`).
4. Copy the Project URL, Anon Key, Service Role Key, and JWT Secret (under Settings -> API).

### Deploy Backend (Render)
1. Create a **Web Service** on [render.com](https://render.com) connected to your repository.
2. Configure settings:
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Set Environment Variables in Render:
   - `DATABASE_URL`: Your Supabase connection string.
   - `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`.
   - `GEMINI_API_KEY`: Your Google AI Studio API key.
   - `FRONTEND_URL`: Your Vercel frontend URL.

### Deploy Frontend (Vercel)
1. Import the repository into [vercel.com](https://vercel.com).
2. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** `Vite`
3. Set Environment Variables in Vercel:
   - `VITE_API_BASE_URL`: `https://your-render-backend.onrender.com/api`
   - `VITE_SUPABASE_URL`: `https://your-project.supabase.co`
   - `VITE_SUPABASE_ANON_KEY`: Your Supabase publishable anonymous key.
4. Deploy.

---

## 10. Verification of Done Checklist

- [x] Full-stack architecture with separate `frontend/` and `backend/`.
- [x] Zero fabricated dummy data or fake customer records.
- [x] Working Supabase Auth and verified token parsing.
- [x] Deal creation and cryptographically hashed invitation tokens.
- [x] Single-use token acceptance and 403 IDOR rejection.
- [x] Raw conversation import with speaker parsing.
- [x] Google Gemini integration with Pydantic validation & manual fallback.
- [x] Missing-term clarification attributing user answers.
- [x] Plain-language agreement generation with ReportLab legal PDF export.
- [x] Bilateral mutual review: Requires both parties to approve the same version.
- [x] Amendment management with side-by-side comparison and approval invalidation on edits.
- [x] Tamper-evident SHA-256 hash chaining and active verification endpoint.
- [x] Real database-backed in-app notifications.
- [x] Professional human-designed UI adhering to navy/charcoal aesthetics without generic AI templates.
- [x] 100% automated pytest test suite pass rate.
