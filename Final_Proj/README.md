# AI Fan Engagement Agent

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.100+-green.svg)](https://fastapi.tiangolo.com/)

A sophisticated web-based platform that combines AI-powered interactions with sports fan engagement. Users can chat with an intelligent agent, compete in AI-generated quizzes, predict game outcomes, and earn rewards.

## 🎯 Features

- **Intelligent Chat Interface**: Natural language conversations with AI
- **Dynamic Quiz System**: AI-generated trivia with multiple difficulty levels  
- **Prediction Engine**: AI-powered game outcome predictions
- **Reward System**: Points and badge tracking with leaderboard
- **Persistent Memory**: User profiles and interaction history
- **Multi-Sport Support**: NBA, NFL, Soccer, and more

## 🏗️ Project Structure

```
.
├── backend/              # FastAPI backend
├── frontend/             # Web interface
├── deployment/           # Deployment config
├── scripts/              # Test & utility scripts
├── docs/                 # Documentation
├── README.md             # This file
└── requirements.txt      # Dependencies
```

## 📦 Installation

```bash
# Clone & setup
git clone https://github.com/Prabinr2004/sports-fan-ai-agent.git
cd sports-fan-ai-agent

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
echo "OPENROUTER_API_KEY=your_key" > .env
```

## 🚀 Running

### Backend
```bash
uvicorn backend.app.main:app --reload
```

### Frontend  
```bash
cd frontend && python -m http.server 8001
```

### Complete App
```bash
./deployment/run.sh
```

## 📡 API Endpoints

- `POST /api/chat` - Chat with AI agent
- `GET /api/quiz` - Get quiz questions
- `POST /api/quiz/submit` - Submit answers
- `GET /api/user/<id>` - User profile
- `GET /api/leaderboard` - Rankings

## 🧪 Testing

```bash
python scripts/test_quiz_system.py
python scripts/verify_system.py
```

## 📚 Documentation

- **REFACTORING_SUMMARY.md** - Project restructuring
- **BEFORE_AFTER_COMPARISON.md** - Analysis
- **CHECKLIST.md** - Task reference

## 🛠️ Tech Stack

- **Backend**: FastAPI + Python 3.8+
- **Database**: SQLite
- **AI**: OpenRouter API
- **Frontend**: HTML/CSS/JavaScript

## 🌐 Deployment

Ready for Render.com, Heroku, or local deployment.
See `/deployment/` for configuration files.

## 📝 License

MIT License

---

**Status**: Production Ready ✅  
**Version**: 1.0
