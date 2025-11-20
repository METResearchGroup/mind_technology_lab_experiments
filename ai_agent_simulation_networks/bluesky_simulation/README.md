# Bluesky AI Agent Simulation Platform

A social science research platform for simulating AI agent behaviors based on real Bluesky profiles.

## Architecture

- **Backend**: FastAPI (Python 3.12) with SQLite database
- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **AI**: OpenAI GPT-4 for bio generation and agent behavior
- **Workflow**: LangGraph for simulation orchestration
- **Telemetry**: Opik for tracking

## Project Structure

```
bluesky_simulation/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── db.py                # Database initialization
│   │   ├── models.py            # Pydantic models
│   │   ├── bluesky_client.py    # Bluesky API wrapper
│   │   ├── ingestion.py         # Data ingestion script
│   │   ├── agent_generation.py  # AI bio generation
│   │   └── simulation.py        # LangGraph simulation logic
│   ├── pyproject.toml
│   └── simulation.db            # SQLite database
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Main UI
│   │   └── layout.tsx
│   └── package.json
└── README.md
```

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- `uv` package manager for Python

### Environment Variables

Create a `.env` file in `ai_agent_simulation_networks/` with:

```
BLUESKY_HANDLE="your.handle.bsky.social"
BLUESKY_PASSWORD="your_password"
OPENAI_API_KEY="sk-..."
# Opik (telemetry) - choose one of the following setups
# Local Opik:
# OPIK_USE_LOCAL="1"
#
# Or Opik Cloud / self-hosted:
# OPIK_API_KEY="your_opik_api_key"
# OPIK_WORKSPACE="your_workspace"          # optional
# OPIK_PROJECT_NAME="your_project"         # or OPIK_PROJECT
# OPIK_URL="https://your-opik-server/api"  # optional, for self-hosted
```

### Installation

1. **Backend Setup**:
```bash
cd backend
uv sync
```

2. **Frontend Setup**:
```bash
cd frontend
npm install
```

## Usage

### Step 1: Data Ingestion

Fetch profiles and posts from Bluesky:

```bash
cd backend
python -m app.ingestion
```

This will:
- Fetch 10 Bluesky profiles
- Download their latest 50 posts
- Store in SQLite with `is_seed=True` flag

### Step 2: Generate Agent Bios

Create AI agent personas:

```bash
python -m app.agent_generation
```

This will:
- Use GPT-4 to analyze each user's posts
- Generate detailed persona bios following the specified schema
- Store in `agent_profiles` and `agent_bios` tables

### Step 3: Run the Application

**Terminal 1 - Backend**:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

Visit `http://localhost:3000` to access the UI.

## Simulation Features

### Control Panel
- Set total number of rounds
- Reset simulation
- Step through simulation one turn at a time

### Agent Behavior (per turn)
1. **View Feed**: Get latest 20 posts
2. **Like Posts**: AI decides which posts to like based on persona
3. **Draft Posts**: Generate 3 potential posts
4. **Write Posts**: 5% chance to publish each draft

### Visualization
- Expandable turn-by-turn history
- Per-agent activity (likes and posts)
- Reasons for each like/post decision

## Database Schema

### Tables

- **users**: Bluesky user profiles (seed data)
- **posts**: All posts (seed + simulated)
- **agent_profiles**: AI agent metadata
- **agent_bios**: Detailed persona JSON
- **agent_likes**: Like activity with reasoning
- **simulation_state**: Current simulation status

## API Endpoints

- `GET /` - Health check
- `POST /ingest` - Trigger data ingestion
- `POST /generate-agents` - Generate agent bios
- `POST /simulation/reset` - Reset simulation
- `POST /simulation/step` - Run one turn
- `GET /simulation/state` - Get current state
- `GET /simulation/history` - Get all activity

## Customization

### Hyperparameters

Edit in `backend/app/simulation.py`:
- `POST_PROBABILITY = 0.05` - Chance to write a post per draft
- `FEED_SIZE = 20` - Number of posts in feed
- `PAST_POSTS_LIMIT = 10` - Context for drafting

### Adding Profiles

Edit `TARGET_PROFILES` in `backend/app/ingestion.py`.

## Development Notes

- **Modular Design**: Each component (ingestion, generation, simulation) is independent
- **Type Safety**: Pydantic models enforce schema validation
- **Telemetry**: All simulation steps are tracked with Opik
- **Extensibility**: Easy to add new agent behaviors or metrics

## Future Enhancements

- [ ] Real-time simulation streaming
- [ ] Network graph visualization
- [ ] Custom prompt templates per agent
- [ ] Reply/thread support
- [ ] Export simulation data
- [ ] A/B testing different agent strategies

## License

MIT
