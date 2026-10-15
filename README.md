<div align="center">

# ⚽ FanSphere V2

### Your club. Your matches. Your football universe.

**A full-stack, AI-powered football fan experience** combining personalized club hubs, match predictions, daily quizzes, rewards, and an intelligent football assistant.

[**🌐 Explore Live App**](https://fansphere-v2.vercel.app/) · [**📖 API Documentation**](https://fansphere-v2-api.onrender.com/docs) · [**🩺 API Health**](https://fansphere-v2-api.onrender.com/api/v1/health)

![React](https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

**Live on Vercel + Render · Neon PostgreSQL · Actively developed**

</div>

---

## ✨ Why FanSphere?

Football fandom is more than checking a score. FanSphere brings the experience together in one personalized platform: follow your clubs, explore matches, test your knowledge, make predictions, and earn rewards as you go.

Originally developed as a college **Sports Fan AI Agent**, FanSphere V2 grew into a redesigned full-stack application with user accounts, persistent progress, a modern React interface, historical-data machine-learning predictions, and a bounded AI assistant.

> **Try it:** [fansphere-v2.vercel.app](https://fansphere-v2.vercel.app/)  
> The Render free-tier backend may need time to wake after inactivity. Football-data coverage and AI availability depend on external services.

## 🚀 What you can do

| Experience | Highlights |
| :--- | :--- |
| 🏟️ **My Club** | Choose a primary team, follow favorites, and explore club and squad information |
| 📅 **Match Center** | Browse fixtures and results, compare teams, and save fan match picks |
| 📊 **ML Predictions** | Explore historical-data-driven match outcome estimates and analysis |
| 🧠 **Daily Quizzes** | Play club-focused quiz levels, build streaks, and earn in-app XP |
| 💎 **Gem Wallet** | Track Gems and XP, exchange eligible XP, and unlock analysis features |
| 🎁 **Daily Rewards** | Earn **+1 Gem on login once per UTC day**; rewarded videos are marked **Coming Soon** |
| 🏆 **Progress & Rankings** | Follow achievements, fan rank, prediction history, and leaderboards |
| 🤖 **FanSphere AI** | Ask football and app questions; authenticated, read-only tools can retrieve selected account progress |

FanSphere's picks, XP, and Gems are **in-app engagement features—not real-money betting**. ML predictions are estimates, not guarantees.

## 🖥️ Live application

<div align="center">

### [**▶ Open FanSphere V2**](https://fansphere-v2.vercel.app/)

**Frontend:** Vercel · **API:** Render · **Production database:** Neon PostgreSQL

</div>

**Suggested portfolio screenshots:** Login / club dashboard · Match Center · Quiz · Gem Wallet · AI assistant. Screenshots are intentionally not embedded until reviewed images are available; this avoids showing outdated UI or private user data.

## 🛠️ Technology stack

| Layer | Tools |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, CSS, Lucide icons |
| **Backend** | Python, FastAPI, Pydantic, SQLAlchemy |
| **Database** | SQLite for local development; Neon PostgreSQL in production |
| **Machine learning** | Python, scikit-learn, historical football data |
| **AI integration** | OpenRouter for assistant responses and optional match explanations |
| **Football data** | football-data.org integration, caching and fallback logic |
| **Deployment** | Vercel (frontend), Render (backend) |
| **Validation** | TypeScript checks, Vite build, Pytest backend tests |

## 🧩 How it works

```text
                       ┌───────────────────────────┐
                       │   React + TypeScript UI   │
                       │   Club · Matches · Wallet │
                       └─────────────┬─────────────┘
                                     │ /api/v1
                                     ▼
                       ┌───────────────────────────┐
                       │      FastAPI backend      │
                       ├───────────────────────────┤
                       │ Auth & profiles           │
                       │ Clubs, fixtures & picks   │
                       │ Quizzes, XP & Gems        │
                       │ ML predictions            │
                       │ FanSphere AI              │
                       └───────┬───────────┬───────┘
                               │           │
                               ▼           ▼
                        ┌────────────┐ ┌───────────────────┐
                        │ SQLAlchemy │ │ External services │
                        │ SQLite /   │ │ Football provider │
                        │ PostgreSQL │ │ OpenRouter         │
                        └────────────┘ └───────────────────┘
```

**AI boundaries:** FanSphere AI uses authenticated, read-only application tools for selected wallet, quiz, and saved-pick information. It does **not** place picks, spend Gems, change account settings, or retrieve live match data through chat. Predictions, quizzes, and rewards are implemented through separate application services.

## 🧑‍💻 Run locally

**Prerequisites:** Python 3, Node.js/npm, and optional credentials for external integrations.

### 1. Clone the active V2 branch

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

API: **http://localhost:8000** · Docs: **http://localhost:8000/docs**

Set your own values in `backend/.env`. AI features require an `OPENROUTER_API_KEY`; some football-provider features may require `FOOTBALL_API_KEY` and provider configuration. **Never commit credentials.**

### 3. Start the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

App: **http://localhost:5173** · Vite proxies `/api` to the local backend.

### 4. Run checks

```bash
# From frontend/
npx tsc --noEmit
npm run build

# From backend/ (with the virtual environment active)
pytest
```

These are the available local validation commands, not a claim that every backend test passes in every environment.

## 📁 Repository map

| Path | Contents |
| :--- | :--- |
| `frontend/` | FanSphere V2 React and TypeScript application |
| `backend/app/api/` | FastAPI routes |
| `backend/app/services/` | Core football, quiz, economy, and AI logic |
| `backend/app/ml/` | Prediction pipelines and ML research |
| `backend/tests/` | Backend tests |
| `docs/` | Technical and ML documentation |
| `Final_Proj/` | Preserved original project archive |

### Project history and branches

- **`main`** — original Sports Fan AI Agent baseline.
- **`v2-development`** — active FanSphere V2 application and live backend deployment source.
- **`Final_Proj/`** — original version retained for historical context.

V2 represents a substantial redesign, not just a visual reskin: it introduces a modern client, account-backed fan experience, richer football workflows, and a more structured backend.

## 🔒 Security and limitations

- Use the supplied `.env.example` templates; keep keys, local databases, generated artifacts, and production records out of Git.
- Do not expose API credentials through frontend `VITE_*` variables.
- Football fixtures, squads, and availability depend on provider coverage, caching, and configuration.
- AI responses and ML probabilities may be inaccurate.
- The application is an evolving portfolio project; some features may change or be temporarily unavailable.

## 👨‍💻 About the developer

**Prabin Roka** — Computer Science, Mathematics & Digital Marketing student.

I built FanSphere to combine my interests in football, software engineering, machine learning, and interactive digital experiences. It started as an AI agent project and evolved into a deployed full-stack application that I continue to improve.

**[Personal portfolio](https://prabinr2004.github.io/)** · **[GitHub profile](https://github.com/Prabinr2004)** · **[Live FanSphere](https://fansphere-v2.vercel.app/)**

---

<div align="center">

**Built for football fans, with code, curiosity, and a love of the game. ⚽**

</div>
