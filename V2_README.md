# Sports Fan AI Agent V2

V2 is developed on the `v2-development` branch while the original college project remains preserved on `main`.

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
fastapi dev app/main.py
```

Backend:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

SQLite is the zero-setup local default. PostgreSQL will become the production database once the initial vertical slice is stable.

### Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:
- http://localhost:5173

Vite proxies `/api` calls to the FastAPI server on port 8000.

## Current V2 status

- [x] Protected V2 development branch
- [x] Architecture document
- [x] Modular FastAPI application foundation
- [x] Environment-based configuration
- [x] SQLite-local / PostgreSQL-ready SQLAlchemy session
- [x] User, team, and favorite-team models
- [x] Football provider contract
- [x] Health API
- [x] Team-search API contract
- [x] React + TypeScript + Vite dashboard shell
- [x] Responsive desktop/mobile styling
- [x] Frontend/backend connection indicator
- [ ] Authentication
- [ ] Database migrations
- [ ] Live football provider
- [ ] Team search/results
- [ ] Primary/favorite team persistence
- [ ] ML prediction pipeline
- [ ] Daily quiz/streaks/XP
- [ ] OpenRouter tool-calling assistant

See `docs/V2_ARCHITECTURE.md` for the full roadmap.
