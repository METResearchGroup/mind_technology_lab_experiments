# System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                     (Next.js Frontend)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Control Panel│  │  Simulation  │  │   History    │         │
│  │              │  │    Status    │  │   Viewer     │         │
│  │ - Rounds     │  │ - Turn       │  │ - Per Turn   │         │
│  │ - Reset      │  │ - Progress   │  │ - Per Agent  │         │
│  │ - Step       │  │              │  │ - Likes/Posts│         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Endpoints                          │  │
│  │  POST /simulation/reset  │  POST /simulation/step        │  │
│  │  GET  /simulation/state  │  GET  /simulation/history     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LANGGRAPH SIMULATION ENGINE                  │  │
│  │                                                            │  │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐     │  │
│  │  │ Fetch Feed │───▶│ Decide     │───▶│ Draft      │     │  │
│  │  │            │    │ Likes      │    │ Posts      │     │  │
│  │  └────────────┘    └────────────┘    └────────────┘     │  │
│  │                          │                  │             │  │
│  │                          ▼                  ▼             │  │
│  │                    ┌────────────┐    ┌────────────┐     │  │
│  │                    │ Save Likes │    │ Write Posts│     │  │
│  │                    └────────────┘    └────────────┘     │  │
│  │                                                            │  │
│  │  @track (Opik Telemetry) ──────────────────────────────▶ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   AI COMPONENTS                           │  │
│  │  ┌──────────────────┐         ┌──────────────────┐       │  │
│  │  │  Bio Generation  │         │  Agent Behavior  │       │  │
│  │  │  (GPT-4o)        │         │  (GPT-4o)        │       │  │
│  │  │                  │         │                  │       │  │
│  │  │ - Analyze posts  │         │ - Like decisions │       │  │
│  │  │ - Extract traits │         │ - Post drafting  │       │  │
│  │  │ - Build persona  │         │ - Reasoning      │       │  │
│  │  └──────────────────┘         └──────────────────┘       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SQLITE DATABASE                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    users     │  │    posts     │  │agent_profiles│         │
│  │ (seed data)  │  │(seed+simul.) │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ agent_bios   │  │ agent_likes  │  │simulation_   │         │
│  │ (JSON)       │  │ (w/ reasons) │  │   state      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                         ▲
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                   DATA INGESTION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Bluesky API Client (atproto)                 │  │
│  │                                                            │  │
│  │  - Fetch user profiles                                    │  │
│  │  - Fetch author feeds (50 posts per user)                │  │
│  │  - Authentication & session management                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

EXTERNAL SERVICES:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Bluesky    │  │   OpenAI     │  │  Opik Comet  │
│   (AT Proto) │  │   (GPT-4o)   │  │  (Telemetry) │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Data Flow

### 1. Initialization Phase
```
Bluesky API → Ingestion → SQLite (users, posts)
                ↓
         Agent Generation (GPT-4)
                ↓
         SQLite (agent_profiles, agent_bios)
```

### 2. Simulation Phase (Per Turn)
```
For each agent:
  1. SQLite → Get Feed (20 posts)
  2. SQLite → Get Agent Bio
  3. GPT-4 → Decide Likes (with reasoning)
  4. SQLite ← Save Likes
  5. GPT-4 → Draft Posts (3 drafts with reasoning)
  6. Random(p=0.05) → Write Post?
  7. SQLite ← Save Post (if written)
  8. Opik ← Track telemetry
```

### 3. Visualization Phase
```
Frontend → GET /simulation/state → Backend → SQLite
Frontend → GET /simulation/history → Backend → SQLite
Frontend ← JSON response ← Backend ← Query results
```

## Key Design Decisions

1. **FastAPI + Next.js**: Separation of concerns, better state management
2. **LangGraph**: Structured workflow for agent behavior
3. **Opik Telemetry**: Track all simulation steps for analysis
4. **SQLite**: Simple, file-based, perfect for research
5. **Pydantic**: Type safety and schema validation
6. **Step-through UI**: Allows careful observation of agent behavior
