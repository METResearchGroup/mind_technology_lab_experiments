# Quick Start Guide

## Prerequisites Check

✅ Python 3.12+ installed  
✅ Node.js 18+ installed  
✅ `uv` package manager installed  
✅ `.env` file configured in `ai_agent_simulation_networks/`

## Initial Setup (One-Time)

### 1. Install Dependencies

**Backend:**
```bash
cd backend
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
```

### 2. Ingest Data from Bluesky

```bash
cd backend
python -m app.ingestion
```

This will fetch 10 Bluesky profiles and their latest 50 posts (~5 minutes).

### 3. Generate AI Agent Bios

```bash
python -m app.agent_generation
```

This uses GPT-4 to create detailed personas for each agent (~10 minutes).

### 4. Verify Setup

```bash
cd ..
python test_db.py
```

You should see:
```
✓ Found 10 seed users
✓ Found ~500 seed posts
✓ Found 10 agent profiles
✓ Found 10 agent bios
✅ Database looks good!
```

## Running the Application

### Option 1: Using the Startup Script (Recommended)

```bash
./start.sh
```

This starts both backend and frontend automatically.

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Using the Application

1. Open http://localhost:3000 in your browser
2. Set the number of rounds (default: 10)
3. Click "Run Next Turn" to step through the simulation
4. Expand turns and agents to see detailed activity

## Simulation Behavior

Each turn, every agent will:
1. **View Feed**: See the latest 20 posts
2. **Like Posts**: AI decides which posts align with their persona
3. **Draft Posts**: Generate 3 potential posts
4. **Write Posts**: 5% chance to publish each draft

## Troubleshooting

### Backend won't start
- Check `.env` file exists and has correct credentials
- Verify database exists: `ls backend/simulation.db`
- Run `python test_db.py` to check data

### Frontend won't connect
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify `next.config.ts` has correct proxy settings

### No agents in simulation
- Run data ingestion: `python -m app.ingestion`
- Run agent generation: `python -m app.agent_generation`

### Simulation not progressing
- Check backend logs for errors
- Verify OpenAI API key is valid
- Check Opik telemetry is configured

## Next Steps

- Adjust `POST_PROBABILITY` in `backend/app/simulation.py`
- Add more Bluesky profiles in `backend/app/ingestion.py`
- Customize prompts in `backend/app/simulation.py`
- Export simulation data for analysis
