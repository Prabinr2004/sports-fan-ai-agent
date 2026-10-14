# FanSphere V2 — Development Notes

> For the main project overview, screenshots guidance, architecture, and setup, see [README.md](README.md).

FanSphere V2 is the modern successor to the original **Sports Fan AI Agent** college project. The original project is preserved on `main` and in `Final_Proj/`. The V2 code is maintained on `v2-development`.

## Implemented in V2

- React + TypeScript + Vite premium football UI
- FastAPI backend and SQLAlchemy/SQLite persistence
- Account authentication, user profiles and team preferences
- Primary club and followed-club dashboards, squad views, fixtures and results
- Match Center, fan predictions and historical ML model outlook
- Club-based quizzes, daily rewarded rounds, XP, streaks and progression
- Fan ranks, badges, leaderboard and prediction history
- Gem Wallet, XP exchange and analysis access
- FanSphere AI chat through OpenRouter (requires backend API key)
- Backend tests and frontend TypeScript/build scripts

## Important boundaries

- The V2 chat is **conversational and read-only**, not a tool-executing agent. It cannot award XP, change account data, create official quizzes or retrieve live football data.
- ML match predictions are estimates from historical data, not guarantees.
- The football provider may have limited coverage or require API credentials.
- The V2 branch is an evolving portfolio project; deployment and production readiness should be verified separately.

## Local setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
cp .env.example .env
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Add personal API credentials to `backend/.env` as needed. Never commit the populated file.

## References

- [Architecture notes](docs/V2_ARCHITECTURE.md)
- [ML data roadmap](docs/ML_DATA_ROADMAP.md)
- [Original project archive](Final_Proj/)
