import json
import random
import uuid
from datetime import datetime
from typing import List, Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import opik
from app.db import get_db_connection
from app.models import AgentBioSchema
import asyncio
from queue import Queue
import sys
from io import StringIO
from time import perf_counter
from app.evals.opik_metrics import score_with_opik_metrics

# Global event queue for real-time updates
event_queue = Queue()

def emit_event(event_type: str, data: Dict[str, Any]):
    """Emit an event to the event queue for SSE streaming."""
    event_queue.put({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })


def current_timestamp_str() -> str:
    """Return current timestamp in YYYY_MM_DD-HH:MM:SS format for metadata."""
    return datetime.now().strftime("%Y_%m_%d-%H:%M:%S")


def generate_session_id() -> str:
    """Generate a session identifier in the required format."""
    return f"{current_timestamp_str()}_{uuid.uuid4().hex[:6]}"


def build_metadata(session_id: str, **extra: Any) -> Dict[str, Any]:
    """Helper to attach standard metadata (session + timestamp) plus extras."""
    metadata: Dict[str, Any] = {
        "session_id": session_id,
        "timestamp": current_timestamp_str(),
    }
    for key, value in extra.items():
        if value is not None:
            metadata[key] = value
    return metadata

# --- Prompts ---

LIKE_DECISION_PROMPT = """
You are simulating the social media behavior of the following persona:

Name: {name}
Bio: {bio}

You are viewing your social media feed. Here are the latest posts:

{feed_posts}

Your task is to decide which of these posts you would "like".
Consider your persona's interests, values, and personality.
You can like multiple posts, or none.

Output a JSON object with a list of "likes". Each item in the list should have:
- "post_uri": The URI of the post you are liking.
- "reason": A 1-2 sentence explanation of why you liked it.

Format:
{{
  "likes": [
    {{ "post_uri": "...", "reason": "..." }},
    ...
  ]
}}
"""

POST_DRAFTING_PROMPT = """
You are simulating the social media behavior of the following persona:

Name: {name}
Bio: {bio}

Here are the last 10 posts you wrote:
{past_posts}

Here is your current feed (what others are posting):
{feed_posts}

Your task is to draft 3 potential social media posts (tweets) that you might write right now.
Consider your persona, your recent activity, and what's happening in your feed.
For each draft, provide a 1-2 sentence explanation of why you would write this.

Output a JSON object with a list of "drafts".
Format:
{{
  "drafts": [
    {{ "text": "...", "reason": "..." }},
    {{ "text": "...", "reason": "..." }},
    {{ "text": "...", "reason": "..." }}
  ]
}}
"""

# --- Tools / Helpers ---

def get_agent_bio(cursor, agent_handle: str) -> Dict[str, Any]:
    cursor.execute("SELECT bio_json FROM agent_bios WHERE agent_handle = ?", (agent_handle,))
    row = cursor.fetchone()
    if row:
        return json.loads(row['bio_json'])
    return {}

def get_feed(cursor, limit: int = 20) -> List[Dict[str, Any]]:
    # Get latest 20 posts by created_at (when post was written)
    cursor.execute("""
        SELECT uri, author_handle, text, created_at 
        FROM posts 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    return [dict(row) for row in cursor.fetchall()]

def get_agent_past_posts(cursor, agent_handle: str, limit: int = 10) -> List[Dict[str, Any]]:
    cursor.execute("""
        SELECT text, created_at 
        FROM posts 
        WHERE author_handle = ? 
        ORDER BY insert_timestamp DESC 
        LIMIT ?
    """, (agent_handle, limit))
    return [dict(row) for row in cursor.fetchall()]

def save_like(cursor, agent_handle: str, post_uri: str, reason: str, turn: int):
    # Need to fetch post details to save in likes table as per requirement
    cursor.execute("SELECT author_handle, text FROM posts WHERE uri = ?", (post_uri,))
    post = cursor.fetchone()
    if post:
        cursor.execute("""
            INSERT INTO agent_likes (agent_handle, liked_post_uri, liked_post_author, liked_post_text, reason, turn, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (agent_handle, post_uri, post['author_handle'], post['text'], reason, turn, datetime.now()))

def save_post(cursor, agent_handle: str, text: str, turn: int):
    # Generate a fake URI/CID for the simulation post
    fake_uri = f"at://simulation/{agent_handle}/{uuid.uuid4()}"
    fake_cid = f"bafy...{uuid.uuid4()}" # Mock CID
    
    cursor.execute("""
        INSERT INTO posts (uri, cid, author_handle, text, created_at, is_seed, insert_timestamp, turn)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (fake_uri, fake_cid, agent_handle, text, datetime.now().isoformat(), False, datetime.now(), turn))

# --- Simulation Logic ---

class SimulationState(TypedDict):
    turn: int
    agents: List[str]
    session_id: str
    
def run_agent_turn(agent_handle: str, turn: int, session_id: str, turn_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Capture stdout
    stdout_capture = StringIO()
    original_stdout = sys.stdout
    
    try:
        sys.stdout = stdout_capture
        
        print(f"  Running turn {turn} for {agent_handle}...")
        emit_event("agent_start", {
            "agent": agent_handle,
            "turn": turn,
            "session_id": session_id,
            "turn_id": turn_id,
        })
        
        # 1. Get Bio
        bio = get_agent_bio(cursor, agent_handle)
        bio_str = json.dumps(bio.get('summary', {})) + "\n" + json.dumps(bio.get('politics_and_values', {}))
        
        # 2. Get Feed
        feed = get_feed(cursor)
        feed_str = json.dumps([{"author": p['author_handle'], "text": p['text']} for p in feed], indent=2)
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        
        # Prepare feed with URIs for prompts
        feed_with_uris = [{"uri": p['uri'], "author": p['author_handle'], "text": p['text']} for p in feed]
        feed_str_uris = json.dumps(feed_with_uris, indent=2)
        
        # Build chains
        like_chain = ChatPromptTemplate.from_template(LIKE_DECISION_PROMPT) | llm.bind(response_format={"type": "json_object"})
        draft_chain = ChatPromptTemplate.from_template(POST_DRAFTING_PROMPT) | llm.bind(response_format={"type": "json_object"})

        likes_count = 0
        posts_count = 0
        drafts: List[Dict[str, Any]] = []
        likes_data: Dict[str, Any] = {}
        drafts_data: Dict[str, Any] = {}
        like_latency_s: float = 0.0
        draft_latency_s: float = 0.0
        like_tokens: Dict[str, Any] = {}
        draft_tokens: Dict[str, Any] = {}

        # LIKE span
        like_prompt_text = LIKE_DECISION_PROMPT.format(name=agent_handle, bio=bio_str, feed_posts=feed_str_uris)
        with opik.start_as_current_span(
            name="like",
            type="llm",
            metadata=build_metadata(
                session_id,
                agent_handle=agent_handle,
                turn=turn,
                turn_id=turn_id,
                span="like",
            ),
        ) as like_span:
            like_span.model = "gpt-4o"
            like_span.provider = "openai"
            like_input = {
                "name": agent_handle,
                "bio": bio_str,
                "feed_posts": feed_str_uris
            }
            like_span.input = {
                "like_input": like_input,
                "like_prompt": like_prompt_text
            }
            t0 = perf_counter()
            like_result = like_chain.invoke(like_input)
            like_latency_s = perf_counter() - t0
            like_tokens = getattr(like_result, "response_metadata", {}).get("token_usage", {})
            like_span.output = {"response": like_result.content}
            likes_data = json.loads(like_result.content)
            for like in likes_data.get("likes", []):
                save_like(cursor, agent_handle, like['post_uri'], like['reason'], turn)
                print(f"    Liked post by {like.get('post_uri')} because: {like.get('reason')}")
                likes_count += 1
            like_span.metadata = {
                **(like_span.metadata or {}),
                "likes_count": likes_count,
                "latency_s": like_latency_s,
                "token_usage": like_tokens,
            }

        # DRAFT span
        past_posts = get_agent_past_posts(cursor, agent_handle)
        past_posts_str = json.dumps(past_posts, indent=2)
        draft_prompt_text = POST_DRAFTING_PROMPT.format(
            name=agent_handle,
            bio=bio_str,
            past_posts=past_posts_str,
            feed_posts=feed_str
        )
        with opik.start_as_current_span(
            name="draft",
            type="llm",
            metadata=build_metadata(
                session_id,
                agent_handle=agent_handle,
                turn=turn,
                turn_id=turn_id,
                span="draft",
            ),
        ) as draft_span:
            draft_span.model = "gpt-4o"
            draft_span.provider = "openai"
            draft_input = {
                "name": agent_handle,
                "bio": bio_str,
                "past_posts": past_posts_str,
                "feed_posts": feed_str
            }
            draft_span.input = {
                "draft_input": draft_input,
                "draft_prompt": draft_prompt_text
            }
            t1 = perf_counter()
            draft_result = draft_chain.invoke(draft_input)
            draft_latency_s = perf_counter() - t1
            draft_tokens = getattr(draft_result, "response_metadata", {}).get("token_usage", {})
            draft_span.output = {"response": draft_result.content}
            drafts_data = json.loads(draft_result.content)
            drafts = drafts_data.get("drafts", [])
            draft_span.metadata = {
                **(draft_span.metadata or {}),
                "latency_s": draft_latency_s,
                "token_usage": draft_tokens,
            }

        # Decide to write (p=0.05)
        if random.random() < 0.05 and drafts:
            chosen_draft = random.choice(drafts)
            with opik.start_as_current_span(
                name="post",
                type="action",
                metadata=build_metadata(
                    session_id,
                    agent_handle=agent_handle,
                    turn=turn,
                    turn_id=turn_id,
                    span="post",
                ),
            ) as post_span:
                save_post(cursor, agent_handle, chosen_draft['text'], turn)
                post_span.metadata = {
                    **(post_span.metadata or {}),
                    "post_text": chosen_draft.get("text", ""),
                }
            print(f"    Wrote post: {chosen_draft['text']}")
            posts_count = 1

        # Commit DB changes for the agent
        conn.commit()
        
        # Restore stdout and capture logs
        sys.stdout = original_stdout
        log_output = stdout_capture.getvalue()
        score_with_opik_metrics(
            agent_handle=agent_handle,
            turn=turn,
            like_prompt=like_prompt_text,
            like_response=like_result.content,
            draft_prompt=draft_prompt_text,
            draft_response=draft_result.content,
            session_id=session_id,
        )
        
        # Emit completion event with results
        emit_event("agent_complete", {
            "agent": agent_handle,
            "turn": turn,
            "session_id": session_id,
            "turn_id": turn_id,
            "likes_count": likes_count,
            "posts_count": posts_count,
            "log": log_output
        })
        
        # Return minimal counts and log excerpt for parent summarization
        return {
            "likes_count": likes_count,
            "posts_count": posts_count,
            "log_excerpt": log_output[:4000]
        }
        
    except Exception as e:
        sys.stdout = original_stdout
        error_msg = f"Error in agent turn for {agent_handle}: {e}"
        print(error_msg)
        emit_event("agent_error", {
            "agent": agent_handle,
            "turn": turn,
            "session_id": session_id,
            "turn_id": turn_id,
            "error": str(e),
            "log": stdout_capture.getvalue()
        })
        # Surface error minimally in parent span output
        return {
            "agent_handle": agent_handle,
            "turn": turn,
            "error": str(e),
            "thread_id": f"turn-{turn}"
        }
    finally:
        conn.close()

def run_simulation_step(state: SimulationState):
    turn = state['turn']
    session_id = state['session_id']
    turn_id = f"{session_id}_turn_{turn:04d}"
    with opik.start_as_current_trace(
        name=turn_id,
        tags=["turn"],
        metadata=build_metadata(session_id, turn=turn, turn_id=turn_id)
    ) as trace:
        print(f"Starting Turn {turn}")
        emit_event("turn_start", {"turn": turn, "session_id": session_id, "turn_id": turn_id})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all agents
        cursor.execute("SELECT handle FROM agent_profiles")
        agents = [row['handle'] for row in cursor.fetchall()]
        conn.close()
        
        total_likes = 0
        total_posts = 0
        
        for agent in agents:
            # Ensure each agent is a top-level child of the turn trace
            with opik.start_as_current_span(
                name=f"{turn_id}_agent_{agent}",
                type="general",
                metadata=build_metadata(
                    session_id,
                    agent_handle=agent,
                    turn=turn,
                    turn_id=turn_id,
                )
            ) as agent_span:
                result = run_agent_turn(agent, turn, session_id, turn_id)
                if isinstance(result, dict):
                    total_likes += int(result.get("likes_count", 0))
                    total_posts += int(result.get("posts_count", 0))
                    agent_span.metadata = {
                        **(agent_span.metadata or {}),
                        "likes_count": int(result.get("likes_count", 0)),
                        "posts_count": int(result.get("posts_count", 0)),
                        "log_excerpt": result.get("log_excerpt", "")
                    }
        
        # Summarize at the trace level
        trace.metadata = {
            **(trace.metadata or {}),
            "likes_count": total_likes,
            "posts_count": total_posts
        }
        
        emit_event("turn_complete", {"turn": turn, "session_id": session_id, "turn_id": turn_id})
        return {"turn": turn + 1, "agents": agents, "session_id": session_id}

# --- LangGraph Definition ---

workflow = StateGraph(SimulationState)

workflow.add_node("step", run_simulation_step)
workflow.set_entry_point("step")
workflow.add_edge("step", END) # One step at a time for the UI

app = workflow.compile()
