from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Bluesky Data Models ---

class BlueskyUser(BaseModel):
    handle: str
    did: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    is_seed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class BlueskyPost(BaseModel):
    uri: str
    cid: str
    author_handle: str
    text: str
    created_at: str  # String from Bluesky API
    reply_parent: Optional[str] = None
    reply_root: Optional[str] = None
    is_seed: bool = False
    insert_timestamp: datetime = Field(default_factory=datetime.now)

# --- Agent Generation Models ---

class AgentBioSchema(BaseModel):
    source_handle: str
    summary: Dict[str, str]
    basic_profile: Dict[str, Any]
    demographics_inferred: Dict[str, str]
    interests_and_domains: Dict[str, Any]
    politics_and_values: Dict[str, Any]
    online_behavior_style: Dict[str, List[str]]
    personality_and_motivations: Dict[str, List[str]]
    safety_and_uncertainty: Dict[str, Any]

class AgentProfile(BaseModel):
    handle: str  # The AI agent's handle (e.g., "[AI Agent] aoc.bsky.social")
    original_handle: str # FK to BlueskyUser
    
class AgentBio(BaseModel):
    agent_handle: str # FK to AgentProfile
    bio_json: str # JSON string of AgentBioSchema

# --- Simulation Models ---

class AgentLike(BaseModel):
    agent_handle: str
    liked_post_uri: str
    liked_post_author: str
    liked_post_text: str
    reason: str
    turn: int
    timestamp: datetime = Field(default_factory=datetime.now)

class SimulationState(BaseModel):
    current_turn: int = 0
    is_running: bool = False
    total_rounds: int = 10
    session_id: str = ""
