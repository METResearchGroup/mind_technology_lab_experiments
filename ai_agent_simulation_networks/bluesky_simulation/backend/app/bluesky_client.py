import os
from atproto import Client
from typing import List, Dict, Any
from dotenv import load_dotenv

# Try to find .env file
current_dir = os.path.dirname(os.path.abspath(__file__))
# app/ -> backend/ -> bluesky_simulation/ -> ai_agent_simulation_networks/
env_path = os.path.join(current_dir, "../../../.env")
if not os.path.exists(env_path):
    # Try relative to CWD if running from backend/
    env_path = os.path.abspath("../../.env")

print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

class BlueskyClient:
    def __init__(self):
        self.client = Client()
        self.handle = os.getenv("BLUESKY_HANDLE")
        self.password = os.getenv("BLUESKY_PASSWORD")
        
        if not self.handle or not self.password:
             # Fallback for debugging
             print(f"Env vars - HANDLE: {self.handle}, PASS: {'*' * len(self.password) if self.password else 'None'}")
             raise ValueError(f"BLUESKY_HANDLE and BLUESKY_PASSWORD must be set in .env. Checked path: {env_path}")
        
        self.client.login(self.handle, self.password)

    def get_profile(self, actor: str) -> Dict[str, Any]:
        try:
            profile = self.client.get_profile(actor=actor)
            return profile.dict()
        except Exception as e:
            print(f"Error fetching profile for {actor}: {e}")
            return None

    def get_author_feed(self, actor: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            # get_author_feed returns a FeedViewPost list
            feed = self.client.get_author_feed(actor=actor, limit=limit)
            posts = []
            for item in feed.feed:
                posts.append(item.post.dict())
            return posts
        except Exception as e:
            print(f"Error fetching feed for {actor}: {e}")
            return []
