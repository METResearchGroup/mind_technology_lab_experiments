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

from models import MODELS, MODEL_PRICING

# Load environment variables
load_dotenv(find_dotenv())

# Configuration
OPIK_API_KEY = os.getenv("OPIK_API_KEY")
OPIK_WORKSPACE = os.getenv("OPIK_WORKSPACE")
OPIK_PROJECT = "OpenAI rate limit testing (for r/aita project)"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPIK_API_KEY:
    print("Warning: OPIK_API_KEY not found in .env")
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in .env")

# Configure Opik globally to use the correct project
opik.configure(use_local=False)

# Initialize Opik
opik_client = Opik(
    api_key=OPIK_API_KEY,
    workspace=OPIK_WORKSPACE,
    project_name=OPIK_PROJECT
)

# Initialize OpenAI client
client_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
client_openai = track_openai(client_openai, project_name=OPIK_PROJECT)

# Initialize OpenRouter client (using AsyncOpenAI compatible client)
client_openrouter = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)
# Also track OpenRouter client
client_openrouter = track_openai(client_openrouter, project_name=OPIK_PROJECT)


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
async def generate_response(submission, request_id, run_id, model_alias="gpt-4o-mini"):
    """Generate a response for a given submission using the specified model."""
    
    start_time = time.time()
    
    # Determine model ID and client to use
    model_id = MODELS.get(model_alias, "gpt-4o-mini")
    
    if model_alias == "gpt-4o-mini":
        client = client_openai
    else:
        client = client_openrouter
        
    try:
        prompt = f"You are a helpful assistant. A user on r/AITA posted the following. Please provide a thoughtful response judging whether they are the asshole or not.\n\nSubmission:\n{submission}"
        
        # Prepare request arguments
        request_kwargs = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "You are a helpful Reddit bot."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300
        }
        
        # For OpenRouter requests, ignore problematic providers like Together
        if client == client_openrouter:
            request_kwargs["extra_body"] = {
                "provider": {
                    "ignore": ["Together"]
                }
            }
        
        response = await client.chat.completions.create(**request_kwargs)
        
        end_time = time.time()
        duration = end_time - start_time
        
        usage = response.usage
        if usage:
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
        else:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
        
        # Cost calculation
        pricing = MODEL_PRICING.get(model_id, {"input": 0, "output": 0})
        cost = (prompt_tokens * pricing["input"] / 1_000_000) + (completion_tokens * pricing["output"] / 1_000_000)
        
        return {
            "id": request_id,
            "status": "success",
            "duration": duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "run_id": run_id,
            "model": model_alias,
            "model_id": model_id,
            "submission": submission
        }
        
    except Exception as e:
        end_time = time.time()
        print(f"Request {request_id} ({model_alias}) failed: {e}")
        return {
            "id": request_id,
            "status": "error",
            "duration": end_time - start_time,
            "error": str(e),
            "cost": 0,
            "total_tokens": 0,
            "run_id": run_id,
            "model": model_alias,
            "model_id": model_id,
            "submission": submission
        }

async def main():
    parser = argparse.ArgumentParser(description="Run OpenAI rate limit scaling test")
    parser.add_argument("--num_requests", type=int, default=100, help="Number of requests to run")
    parser.add_argument("--concurrency", type=int, default=50, help="Maximum number of concurrent requests")
    parser.add_argument("--log_interval", type=int, default=10, help="Log progress every N requests")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", choices=list(MODELS.keys()), help="Model to use")
    args = parser.parse_args()
    
    # Generate a run ID based on timestamp
    run_id = f"run_{time.strftime('%Y%m%d_%H%M%S')}"
    print(f"Starting Run ID: {run_id}")
    print(f"Using model: {args.model} ({MODELS[args.model]})")
    
    print(f"Loading submissions from {DB_PATH}...")
    submissions = load_submissions_from_db(DB_PATH)
    
    if not submissions:
        print("No submissions found in database.")
        return

    print(f"Found {len(submissions)} unique submissions.")
    
    # Initialize progress tracking
    completed_count = 0
    semaphore = asyncio.Semaphore(args.concurrency)
    
    async def tracked_generate_response(submission, request_id):
        nonlocal completed_count
        async with semaphore:
            # Pass run_id and model to the function
            result = await generate_response(submission, request_id, run_id, args.model)
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
            "concurrency": args.concurrency,
            "model_alias": args.model,
            "model_id": MODELS[args.model],
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
        
    # Save deadletter queue for failed requests
    if failed:
        deadletter_path = f"{output_dir}/deadletter.jsonl"
        with open(deadletter_path, "w") as f:
            for fail in failed:
                json.dump(fail, f)
                f.write("\n")
        print(f"Failed requests saved to {deadletter_path}")
        
    print(f"Results saved to {output_dir}")
    
    # Log summary to Opik (optional, as individual traces are logged automatically via track_openai)
    print("Traces should be visible in Opik workspace.")

if __name__ == "__main__":
    asyncio.run(main())
