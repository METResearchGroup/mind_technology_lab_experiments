import os
import json
import asyncio
import argparse
import sqlite3
import time
import ast
from typing import List
from dotenv import load_dotenv, find_dotenv
from openai import AsyncOpenAI
import tqdm

# Load environment variables
load_dotenv(find_dotenv())

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SAMPLE_POSTS_PATH = "../mech_interp_reddit/SAMPLE_REDDIT_POSTS.jsonl"
DB_PATH = "data.db"

def load_sample_posts(filepath: str) -> List[str]:
    """Load submissions from the file (handling Python literal format)."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            # Try parsing as python literal since it uses triple quotes
            try:
                data = ast.literal_eval(content)
                if isinstance(data, list):
                    return [item['submission'] for item in data if 'submission' in item]
            except (ValueError, SyntaxError):
                pass
            
            # Fallback to JSON
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return [item['submission'] for item in data if 'submission' in item]
            except json.JSONDecodeError:
                pass
            
            # Fallback to JSONL
            submissions = []
            f.seek(0)
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        if 'submission' in item:
                            submissions.append(item['submission'])
                    except:
                        pass
            if submissions:
                return submissions
                
    except Exception as e:
        print(f"Error reading file: {e}")
        
    return []

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seed_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_submission TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    return conn

async def generate_post(client: AsyncOpenAI, sample_posts: List[str]) -> str:
    # Create a few-shot prompt
    prompt = "Generate a creative and realistic r/AmITheAsshole submission. It should follow the style and tone of typical posts on the subreddit (personal conflict, moral dilemma, specific details). Do not include the title, just the body text.\n\n"
    
    for i, post in enumerate(sample_posts[:3]): # Use up to 3 samples
        prompt += f"Example {i+1}:\n{post.strip()}\n\n"
        
    prompt += "New Submission:"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative writer generating Reddit posts for r/AmITheAsshole."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating post: {e}")
        return None

async def main():
    parser = argparse.ArgumentParser(description="Generate fake r/aita posts")
    parser.add_argument("--num_posts", type=int, default=100, help="Number of posts to generate")
    parser.add_argument("--concurrency", type=int, default=10, help="Max concurrent requests")
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment.")
        return

    print(f"Loading samples from {SAMPLE_POSTS_PATH}...")
    sample_posts = load_sample_posts(SAMPLE_POSTS_PATH)
    if not sample_posts:
        print("Failed to load sample posts.")
        return
    print(f"Loaded {len(sample_posts)} samples.")

    conn = init_db(DB_PATH)
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    print(f"Generating {args.num_posts} posts...")
    
    generated_count = 0
    pbar = tqdm.tqdm(total=args.num_posts)
    
    # Semaphore to limit concurrency
    sem = asyncio.Semaphore(args.concurrency)

    async def limited_generate():
        async with sem:
            return await generate_post(client, sample_posts)

    tasks = []
    for _ in range(args.num_posts):
        tasks.append(limited_generate())
    
    # Process in batches or just gather all (Semaphore handles concurrency limit)
    # Using as_completed might be nicer for progress bar
    for future in asyncio.as_completed(tasks):
        result = await future
        if result:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO seed_posts (generated_submission, timestamp) VALUES (?, ?)", (result, time.time()))
            conn.commit()
            generated_count += 1
        pbar.update(1)
            
    pbar.close()
    conn.close()
    print(f"\nDone. Generated {generated_count} posts and saved to {DB_PATH}.")

if __name__ == "__main__":
    asyncio.run(main())

