# AI Fan Engagement Agent

A web-based agentic application where sports fans can chat with an AI, take quizzes, predict game outcomes, and earn points and badges.

Built as a CS final at the College of Idaho.

---

## Overview

This project focuses on building an agentic system where the AI decides how to respond by selecting between tools — rather than just generating text. It maintains long-term memory across sessions to personalize each user's experience.

---

## Tech Stack

- **Python / FastAPI** — backend API and agent orchestration
- **OpenRouter API** — LLM access for chat, quiz generation, and predictions
- **SQLite** — persistent storage for user profiles, quiz history, and predictions
- **MCP tool architecture** — modular agent decision-making
- **Vanilla JS / HTML / CSS** — frontend UI
- **Deployed on Render**

---

## Agent Capabilities

### MCP Tools

1. **Quiz Generator** — generates sports trivia questions based on team, difficulty, and count using an LLM via OpenRouter API
2. **Prediction Engine** — predicts match outcomes using team stats and historical context, returns a result with explanation
3. **Fan Reward Tracker** — updates user points, badges, and leaderboard rankings based on quiz and prediction activity

### Long-Term Memory

User data is stored in SQLite across sessions. The agent remembers:
- User profiles
- Quiz history and scores
- Past predictions
- Total points and badges earned

---

## Setup

### Prerequisites
- Python 3.8+
- OpenRouter API key

### Backend

```bash
git clone https://github.com/Prabinr2004/CSCI_Final_proJect
cd CSCI_Final_proJect/Final_Proj/backend
pip install -r requirements.txt
```

Create a `.env` file and add your API key:
OPENROUTER_API_KEY=your_key_here

Run the server:
```bash
python -m uvicorn app.main:app --reload
```

API available at `http://localhost:8000`

### Frontend

```bash
cd ../frontend
python -m http.server 8001
```

Access at `http://localhost:8001`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to agent |
| GET | `/api/user/<user_id>` | Get user profile |
| GET | `/api/leaderboard` | Get top performers |
| GET | `/api/quiz` | Get available quizzes |
| POST | `/api/quiz/submit` | Submit quiz answers |
