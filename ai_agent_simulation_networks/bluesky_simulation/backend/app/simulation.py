import json
import random
from datetime import datetime
from typing import List, Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from opik import track
from app.db import get_db_connection
from app.models import AgentBioSchema
import asyncio
from queue import Queue
import sys
from io import StringIO

# Global event queue for real-time updates
event_queue = Queue()

def emit_event(event_type: str, data: Dict[str, Any]):
    """Emit an event to the event queue for SSE streaming."""
    event_queue.put({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })

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
    import uuid
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
    
@track
def run_agent_turn(agent_handle: str, turn: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Capture stdout
    stdout_capture = StringIO()
    original_stdout = sys.stdout
    
    try:
        sys.stdout = stdout_capture
        
        print(f"  Running turn {turn} for {agent_handle}...")
        emit_event("agent_start", {"agent": agent_handle, "turn": turn})
        
        # 1. Get Bio
        bio = get_agent_bio(cursor, agent_handle)
        bio_str = json.dumps(bio.get('summary', {})) + "\n" + json.dumps(bio.get('politics_and_values', {}))
        
        # 2. Get Feed
        feed = get_feed(cursor)
        feed_str = json.dumps([{"author": p['author_handle'], "text": p['text']} for p in feed], indent=2)
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        
        # 3. Decide Likes
        like_chain = ChatPromptTemplate.from_template(LIKE_DECISION_PROMPT) | llm.bind(response_format={"type": "json_object"})
        like_prompt_text = LIKE_DECISION_PROMPT.format(name=agent_handle, bio=bio_str, feed_posts=feed_str)
        
        # keep raw inputs/outputs for telemetry
        telemetry: Dict[str, Any] = {
            "agent_handle": agent_handle,
            "turn": turn,
            "like_input": {},
            "like_output_raw": None,
            "draft_input": {},
            "draft_output_raw": None
        }
        
        try:
            like_inputs_initial = {
                "name": agent_handle,
                "bio": bio_str,
                "feed_posts": feed_str
            }
            like_result = like_chain.invoke(like_inputs_initial)
            likes_data = json.loads(like_result.content)
            telemetry["like_input"] = {
                "name": agent_handle,
                "bio": bio_str,
                "feed_posts": feed_str
            }
            telemetry["like_output_raw"] = like_result.content
            telemetry["like_prompt"] = like_prompt_text
            telemetry["like_response"] = like_result.content
            print("[telemetry] like_prompt:=\n" + like_prompt_text)
            print("[telemetry] like_response:=\n" + like_result.content)
            
            for like in likes_data.get("likes", []):
                # Find the post URI from the feed list (we need to map back or just trust LLM if it outputs URI correctly)
                # The prompt asks to output "post_uri". We need to provide URIs in the feed.
                # Let's re-format feed_str to include URIs
                pass 
                # Wait, I didn't include URI in feed_str above. Let me fix that in the loop below.
        except Exception as e:
            print(f"    Error in liking: {e}")

        # Re-doing feed string with URIs for the prompt
        feed_with_uris = [{"uri": p['uri'], "author": p['author_handle'], "text": p['text']} for p in feed]
        feed_str_uris = json.dumps(feed_with_uris, indent=2)
        like_prompt_text = LIKE_DECISION_PROMPT.format(name=agent_handle, bio=bio_str, feed_posts=feed_str_uris)
        
        # Retry Like invocation with correct feed
        like_inputs = {
            "name": agent_handle,
            "bio": bio_str,
            "feed_posts": feed_str_uris
        }
        like_result = like_chain.invoke(like_inputs)
        likes_data = json.loads(like_result.content)
        telemetry["like_input"] = {
            "name": agent_handle,
            "bio": bio_str,
            "feed_posts": feed_str_uris
        }
        telemetry["like_output_raw"] = like_result.content
        telemetry["like_prompt"] = like_prompt_text
        telemetry["like_response"] = like_result.content
        print("[telemetry] like_prompt:=\n" + like_prompt_text)
        print("[telemetry] like_response:=\n" + like_result.content)
        likes_count = 0
        for like in likes_data.get("likes", []):
            save_like(cursor, agent_handle, like['post_uri'], like['reason'], turn)
            print(f"    Liked post by {like.get('post_uri')} because: {like.get('reason')}")
            likes_count += 1

        # 4. Draft & Post
        past_posts = get_agent_past_posts(cursor, agent_handle)
        past_posts_str = json.dumps(past_posts, indent=2)
        
        draft_chain = ChatPromptTemplate.from_template(POST_DRAFTING_PROMPT) | llm.bind(response_format={"type": "json_object"})
        draft_prompt_text = POST_DRAFTING_PROMPT.format(
            name=agent_handle,
            bio=bio_str,
            past_posts=past_posts_str,
            feed_posts=feed_str
        )
        
        draft_inputs = {
            "name": agent_handle,
            "bio": bio_str,
            "past_posts": past_posts_str,
            "feed_posts": feed_str # Text only is fine here, or use URIs
        }
        draft_result = draft_chain.invoke(draft_inputs)
        drafts_data = json.loads(draft_result.content)
        telemetry["draft_input"] = {
            "name": agent_handle,
            "bio": bio_str,
            "past_posts": past_posts_str,
            "feed_posts": feed_str
        }
        telemetry["draft_output_raw"] = draft_result.content
        telemetry["draft_prompt"] = draft_prompt_text
        telemetry["draft_response"] = draft_result.content
        print("[telemetry] draft_prompt:=\n" + draft_prompt_text)
        print("[telemetry] draft_response:=\n" + draft_result.content)
        drafts = drafts_data.get("drafts", [])
        
        # 5. Decide to write (p=0.05)
        # Requirement: "iterate through the 3 draft posts and choose to 'write' the post"
        # "let's say with p=0.05 ... we iterate through ... and choose to write"
        # This implies p=0.05 per draft? Or p=0.05 chance to write ANY post?
        # "iterate through the 3 draft posts and choose to 'write' the post" -> ambiguous.
        # Let's assume p=0.05 chance to write ONE post from the drafts.
        
        posts_count = 0
        if random.random() < 0.05 and drafts:
            # Pick one random draft to post
            chosen_draft = random.choice(drafts)
            save_post(cursor, agent_handle, chosen_draft['text'], turn)
            print(f"    Wrote post: {chosen_draft['text']}")
            posts_count = 1
            
        conn.commit()
        
        # Restore stdout and get captured output
        sys.stdout = original_stdout
        log_output = stdout_capture.getvalue()
        
        # Emit completion event with results
        emit_event("agent_complete", {
            "agent": agent_handle,
            "turn": turn,
            "likes_count": likes_count,
            "posts_count": posts_count,
            "log": log_output
        })
        
        # Return telemetry so Opik can display prompt/response content
        telemetry["likes_count"] = likes_count
        telemetry["posts_count"] = posts_count
        telemetry["log_excerpt"] = log_output[:4000]  # avoid overlong payloads
        telemetry["thread_id"] = f"turn-{turn}"
        return telemetry
        
    except Exception as e:
        sys.stdout = original_stdout
        error_msg = f"Error in agent turn for {agent_handle}: {e}"
        print(error_msg)
        emit_event("agent_error", {
            "agent": agent_handle,
            "turn": turn,
            "error": str(e),
            "log": stdout_capture.getvalue()
        })
        # Surface error in telemetry output for Opik
        return {
            "agent_handle": agent_handle,
            "turn": turn,
            "error": str(e),
            "log_excerpt": stdout_capture.getvalue()[:4000],
            "thread_id": f"turn-{turn}"
        }
    finally:
        conn.close()

@track
def run_simulation_step(state: SimulationState):
    turn = state['turn']
    print(f"Starting Turn {turn}")
    emit_event("turn_start", {"turn": turn})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all agents
    cursor.execute("SELECT handle FROM agent_profiles")
    agents = [row['handle'] for row in cursor.fetchall()]
    conn.close()
    
    for agent in agents:
        run_agent_turn(agent, turn)
    
    emit_event("turn_complete", {"turn": turn})
    return {"turn": turn + 1}

# --- LangGraph Definition ---

workflow = StateGraph(SimulationState)

workflow.add_node("step", run_simulation_step)
workflow.set_entry_point("step")
workflow.add_edge("step", END) # One step at a time for the UI

app = workflow.compile()
