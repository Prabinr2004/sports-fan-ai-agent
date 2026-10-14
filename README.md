# FanSphere V2 ⚽
### The football fan hub — personalized, interactive, and AI-powered

FanSphere is a full-stack football fan engagement platform combining club discovery, match insights, machine-learning predictions, daily quizzes, and a personalized AI assistant. Fans can follow clubs, explore fixtures and squads, make match picks for in-app XP, and track their progress through ranks, achievements, and leaderboards.

> **Project evolution:** FanSphere V2 is a major redesign and expansion of my original **Sports Fan AI Agent** college project. The original version is preserved on the `main` branch and in the `Final_Proj/` archive. Active V2 development lives on `v2-development`.

## What's new in V2?

| Area | Original Sports Fan AI Agent | FanSphere V2 |
| --- | --- | --- |
| Interface | HTML, CSS, JavaScript | React, TypeScript, Vite; responsive premium football dashboard |
| AI | Tool-oriented sports agent prototype | In-app conversational FanSphere AI and separate match analysis |
| Football experience | General sports assistant | Primary club, favorites, squad profiles, fixtures, results, match center |
| Predictions | Early prediction tool | Historical-data ML match outlook, fan picks, prediction tracking |
| Quizzes | Dynamic quiz prototype | Club-based quiz levels, daily rewarded challenge, streaks |
| Rewards | Points, badges, leaderboard | Lifetime/spendable XP, ranks, achievements, Gems, analysis unlocks |
| Persistence | SQLite user memory and activity | SQLAlchemy/SQLite-backed accounts, preferences, activity and rewards |

## Features

- **Personalized home:** primary-club hub, club pulse, next match, fan rank and daily challenge.
- **My Team & Favorites:** club details, player profiles, followed teams, fixtures and recent results.
- **Matches & Match Center:** match schedules, fan picks, recent form, team comparison and match analysis.
- **ML match outlook:** estimated outcomes from a trained historical model; probabilities are uncertain, not guarantees.
- **Daily Quiz:** club-specific questions, progressive levels, daily rewarded rounds, XP and streaks.
- **Progress & community:** fan ranks, achievements, leaderboard, prediction record and profile.
- **Gem Wallet:** view spendable XP and Gems, exchange XP, and track analysis unlocks.
- **FanSphere AI:** authenticated football and app-help chat, available as a dedicated page and floating launcher. It uses limited account context; it **does not** retrieve live match data or perform account-changing actions through chat.

Fan picks and rewards are in-app engagement features, **not real-money betting**.

## Technology

| Layer | Stack |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Lucide icons, CSS |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite locally; configurable SQLAlchemy database URL |
| Football data | football-data.org integration and local fallback/caching logic |
| AI | OpenRouter for assistant responses and optional match explanations |
| Predictions | Python-based historical football ML pipeline |
| Quality | Pytest backend tests; TypeScript check and Vite production build |

## Architecture

```text
React + TypeScript frontend
       │
       ▼
FastAPI /api/v1
       ├── Authentication and profiles
       ├── Clubs, favorites, matches and football provider
       ├── Quiz, predictions, XP, Gems and achievements
       ├── Historical ML prediction services
       └── FanSphere AI ──► OpenRouter (optional external LLM)
       │
       ▼
SQLAlchemy + SQLite (local)
```

The **original V1** explored an agentic loop — user request → LLM → tool selection → execution → observation → response — with quiz, prediction, rewards and memory tools. **V2's current chat is intentionally narrower:** it answers questions using provided user context and does not invoke those tools or live football APIs. The quiz, prediction and reward systems operate through their own application features and endpoints.

## Run locally

**Requirements:** Python 3, Node.js/npm, and optional API credentials for connected services.

### 1. Clone and switch to V2

```bash
git clone https://github.com/Prabinr2004/sports-fan-ai-agent.git
cd sports-fan-ai-agent
git switch v2-development
```

### 2. Start the backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
cp .env.example .env
uvicorn app.main:app --reload
```

Configure `backend/.env` with your own `OPENROUTER_API_KEY` for AI chat and analysis. Football-provider features may require `FOOTBALL_API_KEY` and the provider base URL. Never commit actual credentials.

Backend: **http://localhost:8000**  
API documentation: **http://localhost:8000/docs**

### 3. Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Frontend: **http://localhost:5173**. Vite proxies `/api` requests to the local backend.

### 4. Check the project

```bash
cd frontend
npm run build
```

Backend tests (from the repository root, with the Python environment active):

```bash
cd backend
pytest
```

These are commands to run locally; they are not claims that every test has passed on this commit.

## Configuration and security

- Use `backend/.env.example` and `frontend/.env.example` as templates.
- Keep API keys, passwords, local databases, virtual environments and generated build files out of version control.
- The backend protects chat behind authentication; keep API credentials on the server, not in frontend `VITE_*` variables.
- Do not publish real user records, screenshots containing private information, or production database backups.
- Football data availability depends on provider coverage and configuration. AI responses and model probabilities can be inaccurate.

## Repository guide

| Location | Purpose |
| --- | --- |
| `frontend/` | FanSphere V2 React app |
| `backend/app/api/` | FastAPI endpoints |
| `backend/app/services/` | Football, quiz, rewards and AI integrations |
| `backend/app/ml/` | ML experiments, training and prediction utilities |
| `backend/tests/` | Backend test suite |
| `docs/` | Architecture and ML development notes |
| `Final_Proj/` | Original project archive |

## Project status

**FanSphere V2 is an active portfolio project**, not a production service with guaranteed live data. Its current UI and core fan features are implemented, and ongoing work includes testing, reliability and deployment readiness.

**Created and developed by Prabin Roka** · Computer Science, Mathematics & Digital Marketing student.

---
*Built to bring football fandom, AI and interactive learning into one experience.*
