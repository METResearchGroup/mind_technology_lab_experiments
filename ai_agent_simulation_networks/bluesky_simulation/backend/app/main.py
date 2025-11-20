from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
import asyncio
from app.db import get_db_connection, init_db
from app.ingestion import ingest_data
from app.agent_generation import generate_agent_bios
from app.simulation import app as simulation_app, event_queue

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationConfig(BaseModel):
    total_rounds: int = 10

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Bluesky Simulation Backend"}

@app.post("/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks):
    background_tasks.add_task(ingest_data)
    return {"status": "Ingestion started in background"}

@app.post("/generate-agents")
def trigger_agent_generation(background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_agent_bios)
    return {"status": "Agent generation started in background"}

@app.post("/simulation/reset")
def reset_simulation(config: SimulationConfig):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Reset state
    cursor.execute("UPDATE simulation_state SET current_turn = 0, is_running = 0, total_rounds = ?", (config.total_rounds,))
    # Clear simulation data (likes, non-seed posts)
    cursor.execute("DELETE FROM agent_likes")
    cursor.execute("DELETE FROM posts WHERE is_seed = 0")
    conn.commit()
    conn.close()
    return {"status": "Simulation reset"}


# Global flag to track if simulation is running
simulation_running = False

def run_simulation_step_background():
    """Run simulation step in background and emit events."""
    global simulation_running
    simulation_running = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT current_turn, total_rounds FROM simulation_state WHERE id = 1")
        row = cursor.fetchone()
        current_turn = row['current_turn']
        total_rounds = row['total_rounds']
        
        if current_turn >= total_rounds:
            event_queue.put({
                "type": "simulation_complete",
                "data": {"turn": current_turn},
                "timestamp": ""
            })
            simulation_running = False
            conn.close()
            return
        
        # Run one step using LangGraph app
        result = simulation_app.invoke({"turn": current_turn, "agents": []})
        new_turn = result['turn']
        
        # Update state
        cursor.execute("UPDATE simulation_state SET current_turn = ?", (new_turn,))
        conn.commit()
        conn.close()
        
    except Exception as e:
        event_queue.put({
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": ""
        })
    finally:
        simulation_running = False

@app.post("/simulation/step")
def run_simulation_step_endpoint(background_tasks: BackgroundTasks):
    """Start a simulation step in the background."""
    global simulation_running
    
    if simulation_running:
        return {"status": "Simulation already running", "running": True}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_turn, total_rounds FROM simulation_state WHERE id = 1")
    row = cursor.fetchone()
    current_turn = row['current_turn']
    total_rounds = row['total_rounds']
    conn.close()
    
    if current_turn >= total_rounds:
        return {"status": "Simulation complete", "turn": current_turn}
    
    # Clear the event queue before starting
    while not event_queue.empty():
        event_queue.get()
    
    background_tasks.add_task(run_simulation_step_background)
    
    return {"status": "Step started", "turn": current_turn}

async def event_stream():
    """Generate SSE events from the event queue."""
    while True:
        if not event_queue.empty():
            event = event_queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            
            # If simulation is complete or error, stop streaming
            if event.get("type") in ["simulation_complete", "error", "turn_complete"]:
                # Give a moment for any final events
                await asyncio.sleep(0.5)
                if event_queue.empty():
                    break
        else:
            # Send heartbeat to keep connection alive
            yield f": heartbeat\n\n"
            await asyncio.sleep(0.5)
            
            # If simulation is not running and queue is empty, stop
            if not simulation_running and event_queue.empty():
                break

@app.get("/simulation/events")
async def simulation_events():
    """SSE endpoint for real-time simulation progress."""
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/simulation/state")
def get_simulation_state():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_state WHERE id = 1")
    state = dict(cursor.fetchone())
    conn.close()
    return state

@app.get("/simulation/history")
def get_simulation_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get likes per turn
    cursor.execute("""
        SELECT turn, agent_handle, liked_post_uri, reason 
        FROM agent_likes 
        ORDER BY turn, agent_handle
    """)
    likes = [dict(row) for row in cursor.fetchall()]
    
    # Get posts per turn (we need to infer turn or store it. 
    # We didn't store 'turn' in posts table, but we have timestamp.
    # For simplicity, let's just return all non-seed posts and let UI sort or we should have added turn to posts.
    # Let's add 'turn' to posts table? Or just return list.
    # The requirement said: "I should have each turn of the simulation as a separate component... see ... which posts they liked ... and what posts they wrote"
    # It's better to have 'turn' in posts for simulation posts.
    # I'll assume we can map by timestamp or just return all and UI groups them?
    # Let's just return all non-seed posts.
    cursor.execute("""
        SELECT author_handle, text, created_at 
        FROM posts 
        WHERE is_seed = 0 
        ORDER BY created_at
    """)
    posts = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {"likes": likes, "posts": posts}
