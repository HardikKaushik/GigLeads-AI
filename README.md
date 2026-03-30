# GigLeads AI

AI-powered freelance CRM that automates client acquisition end-to-end using a multi-agent system. Finds real jobs from LinkedIn, Indeed, Naukri, and Internshala — scores them with AI — and generates personalized proposals and cover letters automatically.

![Stack](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/Next.js_14-000000?style=flat&logo=next.js&logoColor=white)
![Stack](https://img.shields.io/badge/PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white)
![Stack](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat&logo=tailwindcss&logoColor=white)
![Stack](https://img.shields.io/badge/RapidAPI-0055DA?style=flat&logo=rapidapi&logoColor=white)

## Features

- **Real Job Data** — fetches live listings from LinkedIn, Indeed, Naukri, and Internshala via RapidAPI
- **AI-Powered Scoring** — ranks jobs, gigs, and leads based on your skills and experience
- **Auto Cover Letters** — generates personalized cover letters for top-matching jobs
- **Lead Discovery** — extracts hiring companies from job listings as sales leads
- **Freelance Gigs** — finds contract/freelance opportunities across platforms
- **Pipeline Automation** — one-click pipeline runs all agents in sequence
- **Module Selection** — choose what you need: Leads, Gigs, Jobs (or all three)
- **Auth + Onboarding** — signup, login, and guided onboarding flow

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Next.js Frontend                │
│  Dashboard │ Jobs │ Gigs │ Leads │ Proposals     │
└────────────────────┬────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────┐
│                 FastAPI Backend                   │
│  Auth │ Routes │ Pipeline Orchestrator            │
└────────┬───────────┬───────────┬────────────────┘
         │           │           │
    ┌────▼───┐  ┌────▼───┐  ┌───▼────┐
    │Planner │  │ Finder │  │Proposal│  ... 9 AI Agents
    │ Agent  │  │ Agents │  │ Agent  │
    └────┬───┘  └────┬───┘  └───┬────┘
         │           │          │
    ┌────▼───────────▼──────────▼─────┐
    │         RapidAPI Layer           │
    │  JSearch │ LinkedIn │ Internships│
    └──────────────────────────────────┘
```

### AI Agents

| Agent | Purpose |
|-------|---------|
| **Planner** | Creates strategy based on skills, industry, income goal |
| **Lead Finder** | Discovers hiring companies from job listings |
| **Gig Finder** | Finds freelance/contract opportunities |
| **Job Finder** | Searches LinkedIn, Indeed, Naukri, Internshala |
| **Proposal** | Writes personalized freelance proposals |
| **Cover Letter** | Generates tailored cover letters for jobs |
| **Reviewer** | Quality-gates proposals (rejects score < 70) |
| **Communication** | Drafts follow-ups and outreach messages |
| **Invoice** | Generates professional invoices (HTML/PDF) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), Tailwind CSS, TypeScript |
| **Backend** | FastAPI, Python 3.13, SQLAlchemy ORM |
| **Database** | PostgreSQL 16, Alembic migrations |
| **AI** | Groq API (Llama 3.3 70B) for all agents |
| **Job Data** | RapidAPI — JSearch, LinkedIn Job Search, Internships API |
| **Auth** | JWT tokens, bcrypt password hashing |
| **Infra** | Docker Compose (PostgreSQL + Redis) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- RapidAPI account (free tier works)

### 1. Clone & Setup

```bash
git clone https://github.com/HardikKaushik/GigLeads-AI.git
cd GigLeads-AI
```

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Start Database & Redis

```bash
docker compose up -d
```

### 4. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
cd ..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** — sign up, complete onboarding, and run your first pipeline.

## API Endpoints

```
POST /api/auth/signup              # Create account
POST /api/auth/login               # Sign in
GET  /api/auth/me                  # Current user

PUT  /api/users/profile            # Update skills, portfolio
PUT  /api/users/modules            # Select leads/gigs/jobs
PUT  /api/users/onboarding         # Complete onboarding

POST /api/pipeline/start           # Run automation pipeline
GET  /api/pipeline/{id}/status     # Pipeline progress
GET  /api/pipeline/history         # Past runs

GET  /api/leads                    # List leads
GET  /api/gigs                     # List gigs
GET  /api/jobs                     # List jobs
GET  /api/proposals                # List proposals
GET  /api/invoices                 # List invoices
GET  /api/analytics                # Dashboard stats
```

## Project Structure

```
GigLeads-AI/
├── backend/
│   ├── agents/              # 9 AI agents
│   │   ├── base.py          # Base agent with Groq API
│   │   ├── planner.py
│   │   ├── lead_finder.py
│   │   ├── gig_finder.py
│   │   ├── job_finder.py
│   │   ├── proposal.py
│   │   ├── cover_letter.py
│   │   ├── reviewer.py
│   │   ├── communication.py
│   │   └── invoice.py
│   ├── api/
│   │   ├── auth.py          # JWT authentication
│   │   ├── routes.py        # All API endpoints
│   │   └── schemas.py       # Pydantic models
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models
│   │   └── database.py      # DB connection
│   ├── mcp_server/
│   │   ├── rapidapi_clients.py  # JSearch, LinkedIn, Internships
│   │   └── server.py        # FastMCP tools
│   ├── pipeline/
│   │   └── orchestrator.py  # Multi-agent pipeline
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js pages
│   │   ├── page.tsx         # Dashboard
│   │   ├── jobs/            # Jobs listing
│   │   ├── gigs/            # Gigs listing
│   │   ├── leads/           # Leads listing
│   │   ├── pipeline/        # Pipeline runner
│   │   ├── proposals/       # Proposals
│   │   ├── invoices/        # Invoices
│   │   ├── settings/        # Profile & preferences
│   │   ├── login/
│   │   ├── signup/
│   │   └── onboarding/
│   ├── components/          # Shared UI components
│   ├── lib/
│   │   ├── api.ts           # API client
│   │   └── auth.tsx         # Auth context
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## RapidAPI Setup

Subscribe to these free-tier APIs on [RapidAPI](https://rapidapi.com):

| API | What it provides | Free Tier |
|-----|-----------------|-----------|
| [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) | Indeed, LinkedIn, Naukri, Glassdoor jobs | 200 req/month |
| [LinkedIn Job Search](https://rapidapi.com) | Real LinkedIn jobs with filtering | 500 req/month |
| [Internships API](https://rapidapi.com) | LinkedIn internship listings | 500 req/month |

Add your keys to `.env`:
```
RAPIDAPI_KEY=your_jsearch_key
RAPIDAPI_KEY_2=your_linkedin_internships_key
```

## License

MIT
