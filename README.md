# Sports Fan AI Agent

An AI-powered fan engagement platform that allows users to chat with an intelligent sports assistant, take quizzes, predict game outcomes, and earn rewards through continuous interaction.

## Overview

This project is an agentic AI system where the model does not just respond with text — it dynamically selects tools to perform actions such as generating quizzes, making predictions, and tracking user rewards.

It also maintains long-term user memory to personalize interactions over time.

## Key Features

* 💬 AI Sports Chat Assistant
* 🧠 Tool-based Agent Architecture (Quiz, Prediction, Rewards)
* 🏆 Dynamic Quiz Generation with difficulty levels
* 📊 Game Outcome Prediction Engine
* 🎯 Points, Badges & Leaderboard System
* 💾 Persistent User Memory (SQLite)

## Tech Stack

* Python (FastAPI backend)
* OpenRouter API (LLM orchestration)
* SQLite (persistent storage)
* HTML / CSS / JavaScript (frontend)
* Agentic tool-based architecture (MCP-style design)
* Deployed on Render

## System Design

The AI agent follows a tool-using architecture:

User Input → LLM → Tool Selection → Execution → Observation → Response

Available tools include:

* Quiz generation
* Sports prediction engine
* Reward tracking system
* User memory updates

## Data Persistence

The system stores:

* User profiles
* Quiz history and scores
* Predictions
* Points and badges
* Leaderboard data

## Setup Instructions

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Server runs at:

```
http://localhost:8000
```

### Frontend

```bash
cd frontend
python -m http.server 8001
```

Open:

```
http://localhost:8001
```

## API Endpoints

* `POST /api/chat` → Chat with AI agent
* `GET /api/user/<user_id>` → User profile
* `GET /api/leaderboard` → Rankings
* `GET /api/quiz` → Get quizzes
* `POST /api/quiz/submit` → Submit answers

## Purpose

This project demonstrates an end-to-end AI agent system with tool use, persistent memory, and gamified user engagement.
