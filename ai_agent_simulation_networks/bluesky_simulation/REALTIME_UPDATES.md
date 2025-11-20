# Real-Time Simulation Updates

## Overview

The application has been updated to provide real-time progress tracking during simulation runs. This includes:

1. **Server-Sent Events (SSE)** for streaming progress updates
2. **Collapsible stdout logs** in the UI showing execution traces
3. **Incremental history updates** as each agent completes their turn
4. **Background task execution** for non-blocking simulation runs

## Architecture Changes

### Backend (`backend/app/simulation.py`)

- **Event Queue System**: Added a global `event_queue` using Python's `Queue` to collect events
- **Event Emission**: Added `emit_event()` function to push events to the queue
- **Stdout Capture**: Modified `run_agent_turn()` to capture stdout using `StringIO`
- **Progress Events**: Emit events at key points:
  - `turn_start`: When a turn begins
  - `agent_start`: When an agent starts their turn
  - `agent_complete`: When an agent finishes (includes likes/posts count and logs)
  - `agent_error`: When an agent encounters an error
  - `turn_complete`: When all agents finish a turn
  - `simulation_complete`: When the entire simulation finishes

### Backend API (`backend/app/main.py`)

- **SSE Endpoint**: Added `/simulation/events` GET endpoint for Server-Sent Events
- **Background Execution**: Modified `/simulation/step` to run in background using FastAPI's `BackgroundTasks`
- **Event Streaming**: Implemented `event_stream()` async generator to stream events to clients
- **State Management**: Added global `simulation_running` flag to prevent concurrent runs

### Frontend (`frontend/app/page.tsx`)

- **EventSource Integration**: Connect to SSE endpoint when simulation starts
- **Real-time Log Display**: Added collapsible "Execution Logs" panel with color-coded entries
- **Incremental Updates**: Fetch history after each agent completes (not just at turn end)
- **Event Handling**: Process different event types and update UI accordingly
- **Auto-scroll Logs**: Logs panel with max height and scroll for long outputs

## Features

### 1. Real-Time Progress Tracking

As the simulation runs, you'll see:
- 🚀 Turn start notifications
- 🤖 Each agent starting their turn
- ✅ Agent completion with statistics (likes, posts)
- 🎉 Turn completion
- 🏁 Simulation completion

### 2. Collapsible Logs Panel

Located in the Control Panel, the "Execution Logs" section shows:
- Timestamped entries for each event
- Color-coded messages:
  - **Red**: Errors (❌, 💥)
  - **Green**: Successful completions (✅)
  - **Blue**: Major milestones (🚀, 🎉)
  - **Gray**: Regular progress updates
- Expandable/collapsible to save screen space
- Entry count badge

### 3. Incremental History Updates

Instead of waiting for the entire turn to complete:
- History updates after **each agent** finishes their turn
- You can see results populate in real-time
- Turns auto-expand as they complete

### 4. Non-Blocking Execution

- Simulation runs in a background task
- UI remains responsive during execution
- Can't start multiple simulations simultaneously (protected by flag)

## Usage

1. **Start a Simulation Turn**:
   - Click "Run Next Turn"
   - Logs panel will populate with real-time progress
   - Watch as each agent completes their turn

2. **View Logs**:
   - Click "Execution Logs" header to expand/collapse
   - Scroll through timestamped entries
   - Color coding helps identify important events

3. **Monitor Progress**:
   - Simulation History updates incrementally
   - Expand turns and agents to see details
   - Progress bar shows overall completion

## Technical Details

### SSE Protocol

The `/simulation/events` endpoint streams events in SSE format:

```
data: {"type": "agent_complete", "data": {...}, "timestamp": "..."}

```

- Heartbeat messages (`: heartbeat`) keep connection alive
- Stream closes automatically when turn completes
- Frontend reconnects for each new turn

### Event Data Structure

```typescript
{
  type: string,           // Event type
  data: {                 // Event-specific data
    agent?: string,
    turn?: number,
    likes_count?: number,
    posts_count?: number,
    log?: string,
    error?: string
  },
  timestamp: string       // ISO timestamp
}
```

### Error Handling

- Errors during agent execution are captured and emitted
- Event stream errors close connection gracefully
- UI shows error messages in logs with red highlighting

## Future Enhancements

Potential improvements:
- Persist logs to database for historical review
- Add filtering/search in logs panel
- Export logs to file
- Add pause/resume functionality
- Show agent-specific log streams
- Add performance metrics (execution time per agent)
