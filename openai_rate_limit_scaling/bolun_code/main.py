#!/usr/bin/env python3
"""
Reddit AITA LLM Comment Generator
Async version with concurrent processing and Opik telemetry
"""

import pandas as pd
import json
from openai import AsyncOpenAI
import asyncio
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from opik import Opik, track
from opik.integrations.openai import track_openai

# Load environment variables from both .env files
# Load root .env for Opik credentials
root_env = Path(__file__).parent.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)

# Load local .env for DeepInfra API key
local_env = Path(__file__).parent / ".env"
if local_env.exists():
    load_dotenv(local_env)

# Initialize Opik with credentials from env
OPIK_PROJECT_NAME = "Bolun API scaling testing, 2025-11-20"
opik_client = Opik(
    project_name=OPIK_PROJECT_NAME,
    api_key=os.getenv("OPIK_API_KEY"),
    workspace=os.getenv("OPIK_WORKSPACE")
)

# Configuration
API_KEY = os.getenv("DEEPINFRA_API_KEY")
if not API_KEY:
    raise ValueError("DEEPINFRA_API_KEY not found in environment variables")

BASE_URL = "https://api.deepinfra.com/v1/openai"
INPUT_FILE = "AITA_LLM_results_test_1000.xlsx"
OUTPUT_FILE = "AITA_LLM_results_test_1000.csv"

# Concurrency settings
# 40 concurrent requests keeps us under Opik's 5000 events/min workspace limit
# (40 requests/sec × 3 events each × 60 sec = ~7200/min, but spread over time)
CONCURRENCY_LIMIT = 40

# System prompt
SYSTEM_PROMPT = """You are an AI assistant acting as a member of the Reddit community on the r/AmItheAsshole forum. Your task is to provide a judgment on a user's post.
Your response MUST strictly follow this format:
1.  Start the response on the very first line with ONE of the official voting abbreviations.
2.  Follow it with a single line break.
3.  Provide your reasoning.
4.  Do not add any other text, greetings, or explanations before the abbreviation.

**Voting Guide:**
* **YTA** = You're the Asshole
* **NTA** = Not the Asshole
* **ESH** = Everyone Sucks Here
* **NAH** = No Assholes Here
* **INFO** = Not Enough Info

Post content here:
"""

# Model configuration
MODELS = {
    "deepseek": "deepseek-ai/DeepSeek-V3.1",
    "gpt": "openai/gpt-oss-120b",
    "llama": "meta-llama/Llama-3.3-70B-Instruct"
}

# Global metrics tracking (thread-safe for async)
METRICS = {
    "start_time": None,
    "end_time": None,
    "total_runtime_seconds": 0,
    "requests_by_model": {},
    "latencies_by_model": {},
    "errors_by_model": {},
}


@track(project_name=OPIK_PROJECT_NAME)
async def call_llm(client, model_name, submission_body, max_retries=3):
    """Async LLM API call with Opik tracking"""
    prompt = SYSTEM_PROMPT + "\n" + submission_body
    
    # Track metrics
    start_time = time.time()
    success = False
    error_msg = None
    result = None
    
    for attempt in range(max_retries):
        try:
            # Async API call
            chat_completion = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=60
            )
            success = True
            result = chat_completion.choices[0].message.content
            break
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Async sleep for retry
            else:
                result = f"ERROR: {error_msg}"
    
    # Record metrics (using locks would be overkill for this use case)
    latency = time.time() - start_time
    
    if model_name not in METRICS["requests_by_model"]:
        METRICS["requests_by_model"][model_name] = {"success": 0, "failed": 0}
    if model_name not in METRICS["latencies_by_model"]:
        METRICS["latencies_by_model"][model_name] = []
    if model_name not in METRICS["errors_by_model"]:
        METRICS["errors_by_model"][model_name] = []
    
    if success:
        METRICS["requests_by_model"][model_name]["success"] += 1
    else:
        METRICS["requests_by_model"][model_name]["failed"] += 1
        if error_msg:
            METRICS["errors_by_model"][model_name].append(error_msg)
    
    METRICS["latencies_by_model"][model_name].append(latency)
    
    return result


async def process_single_submission(client, idx, row, semaphore):
    """Process one submission with all 3 models concurrently"""
    submission_body = row['submission_body']
    
    # Skip empty submissions
    if pd.isna(submission_body) or str(submission_body).strip() == "":
        return idx, {}
    
    # Control overall concurrency across all submissions
    async with semaphore:
        # Launch all 3 models at once for this submission
        # ALWAYS process all models (ignore existing responses)
        tasks = {}
        for model_key, model_name in MODELS.items():
            # Create task for this model
            tasks[model_key] = call_llm(client, model_name, str(submission_body))
        
        # Wait for all models to complete for this submission
        results = {}
        if tasks:
            completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for model_key, result in zip(tasks.keys(), completed):
                if isinstance(result, Exception):
                    results[f"{model_key}_comment"] = f"ERROR: {result}"
                else:
                    results[f"{model_key}_comment"] = result
        
        return idx, results


@track(project_name=OPIK_PROJECT_NAME)
def load_excel_data():
    """Load data from Excel file"""
    print(f"Reading Excel file: {INPUT_FILE}...")
    
    # Read existing Excel file
    df = pd.read_excel(INPUT_FILE)
    
    print(f"Loaded {len(df)} submissions from Excel file")
    
    # Ensure model comment columns exist
    for model_key in MODELS.keys():
        column_name = f"{model_key}_comment"
        if column_name not in df.columns:
            df[column_name] = ""
    
    # Clear all existing model responses to force reprocessing
    print(f"  - Clearing all existing model responses for fresh processing")
    for model_key in MODELS.keys():
        column_name = f"{model_key}_comment"
        df[column_name] = ""
    
    print(f"  - All {len(df)} submissions will be processed")
    
    return df


def save_metrics(output_dir, df=None):
    """Save metrics to output directory"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate summary statistics
    total_requests = sum(model_data["success"] + model_data["failed"] 
                        for model_data in METRICS["requests_by_model"].values())
    total_success = sum(model_data["success"] 
                       for model_data in METRICS["requests_by_model"].values())
    total_failed = sum(model_data["failed"] 
                      for model_data in METRICS["requests_by_model"].values())
    
    # Calculate average latencies
    avg_latencies = {}
    for model, latencies in METRICS["latencies_by_model"].items():
        if latencies:
            avg_latencies[model] = {
                "mean_ms": sum(latencies) * 1000 / len(latencies),
                "min_ms": min(latencies) * 1000,
                "max_ms": max(latencies) * 1000,
                "count": len(latencies)
            }
    
    # Create metadata.json
    metadata = {
        "project": "Bolun API scaling testing, 2025-11-20",
        "timestamp": METRICS["start_time"],
        "total_runtime_seconds": METRICS["total_runtime_seconds"],
        "concurrency_limit": CONCURRENCY_LIMIT,
        "models": list(MODELS.keys()),
        "input_file": INPUT_FILE,
        "output_file": OUTPUT_FILE,
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Create output.json with detailed metrics
    output_data = {
        "timestamp": METRICS["start_time"],
        "end_time": METRICS["end_time"],
        "total_runtime_seconds": METRICS["total_runtime_seconds"],
        "concurrency_limit": CONCURRENCY_LIMIT,
        "total_requests": total_requests,
        "total_success": total_success,
        "total_failed": total_failed,
        "success_rate": total_success / total_requests if total_requests > 0 else 0,
        "requests_by_model": METRICS["requests_by_model"],
        "average_latencies_ms": avg_latencies,
        "errors_by_model": {
            model: {"count": len(errors), "sample_errors": errors[:5]}
            for model, errors in METRICS["errors_by_model"].items()
            if errors
        }
    }
    
    with open(output_dir / "output.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    # Save results.csv if dataframe provided
    if df is not None:
        df.to_csv(output_dir / "results.csv", index=False)
    
    print(f"\n📊 Metrics saved to {output_dir}/")
    print(f"   - metadata.json")
    print(f"   - output.json")
    if df is not None:
        print(f"   - results.csv")


@track(project_name=OPIK_PROJECT_NAME)
async def process_data_async(output_dir=None):
    """Async data processing with controlled concurrency"""
    # Initialize metrics
    METRICS["start_time"] = datetime.now().isoformat()
    start_time = time.time()
    
    # Load Excel data (synchronous)
    df = load_excel_data()
    
    # Create shared async client with Opik tracking
    client = track_openai(AsyncOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    ))
    
    # Concurrency control semaphore
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    print(f"\n🚀 Starting async LLM processing for {len(df)} submissions...", flush=True)
    print(f"   Concurrency limit: {CONCURRENCY_LIMIT}", flush=True)
    print(f"   Models per submission: {len(MODELS)}", flush=True)
    print(f"   Max concurrent API calls: ~{CONCURRENCY_LIMIT}", flush=True)
    print(flush=True)
    
    # Create tasks for all submissions
    tasks = []
    for idx, row in df.iterrows():
        task = process_single_submission(client, idx, row, semaphore)
        tasks.append(task)
    
    # Process with progress tracking using as_completed
    completed_count = 0
    completed_requests = 0  # Track individual API requests
    save_interval = 50  # Save every 50 submissions
    total_requests = len(df) * len(MODELS)  # Total API requests expected
    
    print(f"⏳ Processing started - total API requests to make: {total_requests}", flush=True)
    print(flush=True)
    
    for future in asyncio.as_completed(tasks):
        idx, results = await future
        
        # Update dataframe with results
        num_results = 0
        for column, value in results.items():
            df.at[idx, column] = value
            num_results += 1
        
        completed_count += 1
        completed_requests += num_results
        
        # Progress updates every 10 API requests
        if completed_requests % 10 == 0 or completed_count == len(df):
            elapsed = time.time() - start_time
            rate = completed_requests / elapsed if elapsed > 0 else 0
            eta = (total_requests - completed_requests) / rate if rate > 0 else 0
            print(f"  ✓ Completed {completed_requests}/{total_requests} API requests | {completed_count}/{len(df)} submissions | Rate: {rate:.1f} req/sec | ETA: {eta/60:.1f} min", flush=True)
        
        # Save intermediate results
        if completed_count % save_interval == 0 and output_dir:
            temp_output = Path(output_dir) / "results.csv"
            df.to_csv(temp_output, index=False)
            print(f"    💾 Checkpoint saved to {temp_output.name}", flush=True)
    
    # Finalize metrics
    METRICS["end_time"] = datetime.now().isoformat()
    METRICS["total_runtime_seconds"] = time.time() - start_time
    
    # Save final results
    if output_dir:
        save_metrics(output_dir, df)
    else:
        df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n✅ Processing complete!")
    print(f"   Processed {len(df)} submissions")
    print(f"   Total runtime: {METRICS['total_runtime_seconds']:.2f} seconds ({METRICS['total_runtime_seconds']/60:.2f} minutes)")
    print(f"   Average: {len(df)/METRICS['total_runtime_seconds']:.2f} submissions/sec")
    
    # Display column information
    print("\n📋 Output file contains the following columns:")
    for col in df.columns:
        print(f"   - {col}")
    
    return df


def main(output_dir=None):
    """Main entry point"""
    print("=" * 80)
    print("Reddit AITA LLM Comment Generator (Async Version)")
    print("Project: Bolun API scaling testing, 2025-11-20")
    print("=" * 80)
    
    try:
        # Verify input file exists
        if not Path(INPUT_FILE).exists():
            raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")
        
        # Run async processing
        df = asyncio.run(process_data_async(output_dir=output_dir))
        
        print("\n" + "=" * 80)
        print("SUCCESS: All processing completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    import sys
    
    # Accept output directory as command line argument
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None
    main(output_dir=output_dir)
