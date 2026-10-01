# Sports Fan AI Agent — V2 Architecture

## Product goal
Build a personalized football fan platform that combines reliable football data, user-selected teams, daily engagement, machine-learning match predictions, and an AI assistant.

## Core product areas

1. **Personalized Home** — primary team, favorite teams, next matches, recent form, updates, daily challenge.
2. **Team Hub** — overview, current squad, fixtures/results, standings, transfers, staff, statistics.
3. **Search & Favorites** — search any supported team and save favorites.
4. **Predictions** — model-generated home/draw/away probabilities and score estimates, plus user predictions.
5. **Daily Quiz** — team and general football quizzes with persistent attempts.
6. **Gamification** — XP ledger, levels, streaks, badges, weekly/club/global leaderboards.
7. **AI Assistant** — OpenRouter-powered assistant that calls application tools and explains retrieved data/model output rather than inventing football facts.

## Architecture

```text
React + TypeScript frontend
          |
          v
       FastAPI
          |
  +-------+---------+----------------+----------------+
  |                 |                |                |
PostgreSQL     Football provider   ML engine      OpenRouter
  |                 |                |                |
users           teams/squads       Elo             explanations
favorites       fixtures           Poisson         tool selection
XP/badges       standings          classifiers     conversational UI
quiz history    transfers          calibration
predictions     coaches            evaluation
```

## Backend boundaries

```text
backend/app/
  api/          # FastAPI route modules
  core/         # config, security, shared application setup
  database/     # session, base, migrations integration
  models/       # database models
  schemas/      # request/response validation
  services/     # business logic
  providers/    # external football-data provider adapters
  agent/        # OpenRouter agent/tool orchestration
  ml/           # inference code and model artifacts
  tests/        # automated tests
```

`main.py` should only create/configure the FastAPI app and register routers. Business logic must live in services/providers.

## Frontend boundaries

```text
frontend/src/
  components/
  pages/
  layouts/
  hooks/
  services/
  types/
  assets/
```

Target stack: React, TypeScript, Vite, and Tailwind CSS.

## Data principles

- Do not hard-code current squads, rankings, fixtures, transfers, or form.
- External football data is retrieved through a provider adapter so providers can be changed without rewriting the app.
- Cache data according to how often it changes.
- PostgreSQL stores application/user state and selected cached football records where useful.
- OpenRouter is not the source of truth for football facts.

## Prediction principles

The existing rule/random prediction engine is legacy code and will not be used as the V2 model.

V2 prediction pipeline:

1. Collect historical match data.
2. Sort chronologically.
3. Build pre-match features using only information available before kickoff.
4. Establish a simple baseline.
5. Add Elo ratings.
6. Train/evaluate classification models for home/draw/away probabilities.
7. Evaluate a Poisson/Dixon-Coles style goals model for score probabilities.
8. Compare models using held-out future periods.
9. Evaluate probability quality (log loss/Brier score/calibration), not accuracy alone.
10. Store model version with every generated prediction.

Potential features include Elo difference, rolling form, goals for/against, home/away form, rest days, table position, and xG when reliably available.

## User prediction rules

User predictions are an in-app game feature only. They award XP/badges and have no money, wagering, prizes, or betting functionality.

## Gamification model

All point changes should be stored as XP transactions rather than directly mutating an unexplained score.

Examples:
- daily quiz completion
- perfect quiz bonus
- quiz streak bonus
- match prediction submission
- correct outcome
- exact-score achievement

Streaks, levels, and badges are derived from persistent activity records.

## Initial database domains

- users
- teams
- user_favorite_teams
- fixtures
- quiz_questions
- quiz_attempts
- xp_transactions
- badges
- user_badges
- streaks
- user_predictions
- model_predictions

## Development milestones

### M1 — Foundation
- preserve legacy project on `main`
- develop V2 on `v2-development`
- modular FastAPI structure
- environment-based configuration
- PostgreSQL-ready database layer
- React/TypeScript frontend foundation

### M2 — Authentication & personalization
- registration/login
- primary team
- favorite teams
- profile/preferences

### M3 — Football data
- provider adapter
- team search
- team profile
- current squad
- fixtures/results
- home/away filters
- standings
- staff/transfers where provider data supports them

### M4 — Team dashboard
- polished responsive team pages
- loading/error/empty states
- favorites dashboard

### M5 — ML prediction pipeline
- historical dataset
- leakage-safe feature engineering
- baseline + Elo + ML model comparison
- score model
- evaluation and model versioning

### M6 — Prediction experience
- model probabilities
- user predictions
- prediction history
- XP integration

### M7 — Quiz & gamification
- daily quiz
- streaks
- XP levels
- badges
- leaderboards

### M8 — AI & production polish
- OpenRouter tool calling
- model/data explanations
- caching
- tests
- CI/CD
- monitoring
- production deployment

## Legacy migration rule

Existing V1 code is reference material. Each component will be classified as KEEP, REFACTOR, REPLACE, or REMOVE before migration. V2 should not copy large legacy modules unchanged simply to preserve behavior.
