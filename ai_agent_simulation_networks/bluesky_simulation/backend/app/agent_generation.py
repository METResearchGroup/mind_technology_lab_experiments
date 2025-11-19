import json
import os
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.db import get_db_connection
from app.models import AgentBioSchema, AgentProfile

# Load environment variables
from dotenv import load_dotenv
# Reuse the logic from bluesky_client to find .env
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, "../../../.env")
if not os.path.exists(env_path):
    env_path = os.path.abspath("../../.env")
load_dotenv(env_path)

BIO_GENERATION_PROMPT = """
You are an AI researcher building cautious, evidence-based personas from online social media posts.

Your task: given a list of tweets from ONE Bluesky account, infer a concise but rich persona/bio for that account.

Requirements:

1. Use ONLY information that is directly supported by the tweets.
   - If a detail is NOT clearly implied by the tweets, do NOT state it as fact.
   - It is allowed to offer *probabilistic* inferences (e.g., "likely 20s-30s, low confidence"),
     but you MUST clearly mark them with a confidence level.

2. Be especially careful with SENSITIVE attributes (race, ethnicity, religion, gender identity, sexual orientation, health status).
   - Do NOT guess these unless the user explicitly self-identifies them in the tweets.
   - If not explicit, set these fields to "Unknown / not inferable from tweets".

3. Political attributes:
   - Only infer a political leaning if there is repeated, clear political content.
   - Express leanings in cautious, relative terms (e.g., "leans progressive in US politics, low confidence"),
     and back them up with specific tweet evidence.

4. Always separate:
   - (a) direct self-descriptions ("I am a PhD student in economics"),
   - (b) behavioral evidence (what they tweet about and how),
   - (c) your higher-level interpretation with confidence scores.

5. Output a SINGLE JSON object following EXACTLY this schema:

{schema}

6. If a field cannot be filled, use an empty array [] or a descriptive string like "Unknown / not inferable".
7. Include, where possible, tweet IDs in "evidence_tweets" for issue positions.
8. Do NOT include any explanation outside the JSON. Return only valid JSON.

Here is data for one Twitter account.

Handle: {handle}

Each tweet is given as a JSON object with keys "id", "created_at", and "text".

Tweets:
{tweets_json}

Please produce the persona JSON described in the instructions.
"""

def generate_agent_bios():
    print("Starting agent bio generation...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all seed users
    cursor.execute("SELECT handle FROM users WHERE is_seed = 1")
    users = cursor.fetchall()
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(AgentBioSchema, method="function_calling")
    
    for user_row in users:
        handle = user_row['handle']
        print(f"Generating bio for {handle}...")
        
        # Check if agent profile already exists
        agent_handle = f"[AI Agent] {handle}"
        cursor.execute("SELECT handle FROM agent_profiles WHERE handle = ?", (agent_handle,))
        if cursor.fetchone():
            print(f"Agent profile for {handle} already exists. Skipping.")
            continue

        # Get posts for this user
        cursor.execute("SELECT uri, created_at, text FROM posts WHERE author_handle = ? ORDER BY insert_timestamp DESC LIMIT 50", (handle,))
        posts = cursor.fetchall()
        
        tweets_data = []
        for post in posts:
            tweets_data.append({
                "id": post['uri'],
                "created_at": post['created_at'],
                "text": post['text']
            })
            
        tweets_json = json.dumps(tweets_data, indent=2)
        
        # Generate Bio
        prompt = ChatPromptTemplate.from_template(BIO_GENERATION_PROMPT)
        chain = prompt | structured_llm
        
        try:
            # We pass the schema as a string representation for the prompt text, 
            # but structured_llm handles the actual enforcement.
            # The prompt asks for the schema structure, so we can pass the json schema of the pydantic model.
            schema_json = json.dumps(AgentBioSchema.model_json_schema(), indent=2)
            
            result: AgentBioSchema = chain.invoke({
                "schema": schema_json,
                "handle": handle,
                "tweets_json": tweets_json
            })
            
            # Save to DB
            # 1. Create Agent Profile
            cursor.execute("INSERT INTO agent_profiles (handle, original_handle) VALUES (?, ?)", (agent_handle, handle))
            
            # 2. Save Bio
            bio_json_str = result.model_dump_json()
            cursor.execute("INSERT INTO agent_bios (agent_handle, bio_json) VALUES (?, ?)", (agent_handle, bio_json_str))
            
            conn.commit()
            print(f"Successfully generated and saved bio for {agent_handle}")
            
        except Exception as e:
            print(f"Error generating bio for {handle}: {e}")
            
    conn.close()
    print("Agent bio generation complete.")

if __name__ == "__main__":
    generate_agent_bios()
