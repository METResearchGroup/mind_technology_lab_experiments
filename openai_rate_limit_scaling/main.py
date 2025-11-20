import os
import json
import asyncio
import time
import random
import ast
import argparse
import sqlite3
from dotenv import load_dotenv, find_dotenv
from openai import AsyncOpenAI
from opik.integrations.openai import track_openai
from opik import Opik, track
import opik
import tqdm

# Load environment variables
load_dotenv(find_dotenv())

# Configuration
OPIK_API_KEY = os.getenv("OPIK_API_KEY")
OPIK_WORKSPACE = os.getenv("OPIK_WORKSPACE")
OPIK_PROJECT = "OpenAI rate limit testing (for r/aita project)"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ensure Opik uses the correct project name via env var (fallback)
# os.environ["OPIK_PROJECT_NAME"] = OPIK_PROJECT

if not OPIK_API_KEY:
    print("Warning: OPIK_API_KEY not found in .env")

# Configure Opik globally to use the correct project
opik.configure(use_local=False)

# Initialize Opik
opik_client = Opik(
    api_key=OPIK_API_KEY,
    workspace=OPIK_WORKSPACE,
    project_name=OPIK_PROJECT
)

# Initialize OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
client = track_openai(client)

DB_PATH = "data.db"

def load_submissions_from_db(db_path):
    """Load submissions from the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Verify table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='seed_posts'")
        if not cursor.fetchone():
            print("Table 'seed_posts' not found in database.")
            return []
            
        cursor.execute("SELECT generated_submission FROM seed_posts")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows if row[0]]
    except Exception as e:
        print(f"Error reading database: {e}")
        return []

@track(project_name=OPIK_PROJECT)
async def generate_response(submission, request_id, run_id):
    """Generate a response for a given submission."""
    # Add run_id as a tag to the current trace if possible
    try:
        # Try to update tags if context is available
        # opik.opik_context.update_current_trace(tags=[run_id])
        pass 
    except:
        pass

    start_time = time.time()
    try:
        prompt = f"You are a helpful assistant. A user on r/AITA posted the following. Please provide a thoughtful response judging whether they are the asshole or not.\n\nSubmission:\n{submission}"
        
        # Pass tags to the create call if the library supports it, or rely on the wrapper capturing arguments
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful Reddit bot."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        
        # Cost calculation for gpt-4o-mini
        # Input: $0.15 / 1M tokens, Output: $0.60 / 1M tokens
        cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
        
        return {
            "id": request_id,
            "status": "success",
            "duration": duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "run_id": run_id
        }
        
    except Exception as e:
        end_time = time.time()
        print(f"Request {request_id} failed: {e}")
        return {
            "id": request_id,
            "status": "error",
            "duration": end_time - start_time,
            "error": str(e),
            "cost": 0,
            "total_tokens": 0,
            "run_id": run_id
        }

async def main():
    parser = argparse.ArgumentParser(description="Run OpenAI rate limit scaling test")
    parser.add_argument("--num_requests", type=int, default=100, help="Number of requests to run")
    parser.add_argument("--log_interval", type=int, default=10, help="Log progress every N requests")
    args = parser.parse_args()
    
    # Generate a run ID based on timestamp
    run_id = f"run_{time.strftime('%Y%m%d_%H%M%S')}"
    print(f"Starting Run ID: {run_id}")
    
    print(f"Loading submissions from {DB_PATH}...")
    submissions = load_submissions_from_db(DB_PATH)
    
    if not submissions:
        print("No submissions found in database.")
        return

    print(f"Found {len(submissions)} unique submissions.")
    
    # Initialize progress tracking
    completed_count = 0
    
    async def tracked_generate_response(submission, request_id):
        nonlocal completed_count
        # Pass run_id to the function
        result = await generate_response(submission, request_id, run_id)
        completed_count += 1
        if completed_count % args.log_interval == 0:
            print(f"Request {completed_count}/{args.num_requests}")
        return result

    # Prepare requests by cycling through submissions
    tasks = []
    for i in range(args.num_requests):
        submission = submissions[i % len(submissions)]
        tasks.append(tracked_generate_response(submission, i))
    
    print(f"Starting {args.num_requests} requests in parallel...")
    print(f"Logging progress every {args.log_interval} requests.")
    start_total = time.time()
    
    # Run all tasks
    results = await asyncio.gather(*tasks)
    
    end_total = time.time()
    total_runtime = end_total - start_total
    
    # Aggregate results
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    total_cost = sum(r['cost'] for r in successful)
    total_tokens = sum(r['total_tokens'] for r in successful)
    avg_latency = sum(r['duration'] for r in successful) / len(successful) if successful else 0
    
    print("\n" + "="*30)
    print("RESULTS")
    print("="*30)
    print(f"Total Requests: {args.num_requests}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total Runtime: {total_runtime:.2f}s")
    print(f"Total Tokens: {total_tokens}")
    print(f"Total Cost: ${total_cost:.4f}")
    print(f"Avg Latency (success): {avg_latency:.2f}s")
    print("="*30)
    
    # Create output directory with timestamp
    timestamp = time.strftime("%Y_%m_%d-%H:%M:%S")
    output_dir = f"output/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save metadata
    metadata = {
        "timestamp": timestamp,
        "run_id": run_id,
        "runtime_configuration": {
            "num_requests": args.num_requests,
            "model": "gpt-4o-mini",
            "max_tokens": 300,
            "log_interval": args.log_interval,
            "data_source": DB_PATH
        },
        "metrics": {
            "total_runtime": total_runtime,
            "total_requests": args.num_requests,
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "avg_latency": avg_latency
        }
    }
    
    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    # Save results
    with open(f"{output_dir}/results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Results saved to {output_dir}")
    
    # Log summary to Opik (optional, as individual traces are logged automatically via track_openai)
    print("Traces should be visible in Opik workspace.")

if __name__ == "__main__":
    asyncio.run(main())
