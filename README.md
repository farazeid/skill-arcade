# Skill Arcade

## Purpose

Interface for researchers to collect and derive skills and skill hierarchies.

## Tech Stack

- Backend: FastAPI, Python
- Frontend: React, TypeScript, Vite
- Database: TODO
- Hosting:
  - Backend: Cloud Run
  - Frontend: Firebase Hosting

# Run locally

Backend:

```zsh
cd backend
uv sync
uv run uvicorn main:app --reload
```

Frontend:

```zsh
cd frontend
npm install
npm run dev
```
