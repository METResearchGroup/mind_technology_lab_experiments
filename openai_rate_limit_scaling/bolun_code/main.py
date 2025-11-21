#!/usr/bin/env python3
"""
Reddit AITA LLM Comment Generator
Converts notebook functionality to a standalone script with Opik telemetry
"""

import pandas as pd
import json
from openai import OpenAI
from tqdm import tqdm
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
opik_client = Opik(
    project_name="Bolun API scaling testing, 2025-11-20",
    api_key=os.getenv("OPIK_API_KEY"),
    workspace=os.getenv("OPIK_WORKSPACE")
)

# Configuration
API_KEY = os.getenv("DEEPINFRA_API_KEY")
if not API_KEY:
    raise ValueError("DEEPINFRA_API_KEY not found in environment variables")

BASE_URL = "https://api.deepinfra.com/v1/openai"
SUBMISSION_FILE = "final_1000_submissions.json"
COMMENT_FILE = "final_3000_comments.json"
OUTPUT_FILE = "AITA_LLM_results_test_1000.csv"

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

# Global metrics tracking
METRICS = {
    "start_time": None,
    "end_time": None,
    "total_runtime_seconds": 0,
    "requests_by_model": {},
    "latencies_by_model": {},
    "errors_by_model": {},
}


@track
def call_llm(model_name, submission_body, max_retries=3):
    """Call LLM API to get response with Opik tracking"""
    # Wrap OpenAI client with Opik tracking
    openai_client = track_openai(OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    ))
    
    prompt = SYSTEM_PROMPT + "\n" + submission_body
    
    # Track metrics
    start_time = time.time()
    success = False
    error_msg = None
    
    for attempt in range(max_retries):
        try:
            chat_completion = openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=60
            )
            success = True
            result = chat_completion.choices[0].message.content
            break
        except Exception as e:
            error_msg = str(e)
            print(f"    Attempt {attempt + 1}/{max_retries} failed: {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                result = f"ERROR: {error_msg}"
    
    # Record metrics
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
        METRICS["errors_by_model"][model_name].append(error_msg)
    
    METRICS["latencies_by_model"][model_name].append(latency)
    
    return result


@track
def load_json_data():
    """Load data from JSON files and organize into DataFrame"""
    print("Reading JSON files...")
    
    # Read submissions (first 1000)
    submissions = []
    with open(SUBMISSION_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 1000:
                break
            submissions.append(json.loads(line.strip()))
    
    # Read comments and group by submission
    comments_by_sub = {}
    with open(COMMENT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            comment = json.loads(line.strip())
            link_id = comment.get('link_id', '')
            if link_id.startswith('t3_'):
                sub_id = link_id[3:]
            else:
                sub_id = link_id
            
            if sub_id not in comments_by_sub:
                comments_by_sub[sub_id] = []
            comments_by_sub[sub_id].append(comment)
    
    print(f"Read {len(submissions)} submissions")
    
    # Build DataFrame
    data_rows = []
    for sub in submissions:
        sub_id = sub['id']
        sub_comments = comments_by_sub.get(sub_id, [])
        
        # Sort comments by score, take top 3
        sub_comments.sort(key=lambda x: x.get('score', 0), reverse=True)
        top_3 = sub_comments[:3]
        
        row = {
            'submission_id': sub_id,
            'submission_title': sub.get('title', ''),
            'submission_body': sub.get('selftext', ''),
            'submission_score': sub.get('score', 0),
            'submission_author': sub.get('author', ''),
            'submission_created': sub.get('created_utc', ''),
        }
        
        # Add 3 comments
        for i, comment in enumerate(top_3, 1):
            row[f'comment_{i}_body'] = comment.get('body', '')
            row[f'comment_{i}_score'] = comment.get('score', 0)
            row[f'comment_{i}_author'] = comment.get('author', '')
        
        # Add columns for 3 model results (to be filled)
        row['deepseek_comment'] = ""
        row['gpt_comment'] = ""
        row['llama_comment'] = ""
        
        data_rows.append(row)
    
    df = pd.DataFrame(data_rows)
    print(f"Created DataFrame with {len(df)} rows")
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
        "models": list(MODELS.keys()),
        "input_files": [SUBMISSION_FILE, COMMENT_FILE],
        "output_file": OUTPUT_FILE,
    }
    
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Create output.json with detailed metrics
    output_data = {
        "timestamp": METRICS["start_time"],
        "end_time": METRICS["end_time"],
        "total_runtime_seconds": METRICS["total_runtime_seconds"],
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


@track
def process_data(output_dir=None):
    """Process data and call LLMs with Opik tracking"""
    # Initialize metrics
    METRICS["start_time"] = datetime.now().isoformat()
    start_time = time.time()
    
    # Load JSON data
    df = load_json_data()
    
    # Process each row
    print(f"\nStarting LLM processing for {len(df)} items...")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        # Get submission_body
        submission_body = row['submission_body']
        if pd.isna(submission_body) or str(submission_body).strip() == "":
            print(f"  Skipping row {idx + 1} (empty submission_body)")
            continue
        
        print(f"\nProcessing row {idx + 1}:")
        
        # Call each of the 3 models
        for model_key, model_name in MODELS.items():
            column_name = f"{model_key}_comment"
            
            # Skip if already processed
            if pd.notna(row[column_name]) and str(row[column_name]).strip() != "":
                print(f"  - {model_key}: Already processed, skipping")
                continue
            
            print(f"  - Calling {model_key} ({model_name})...")
            
            # Call LLM
            llm_response = call_llm(model_name, str(submission_body))
            
            # Save result
            df.at[idx, column_name] = llm_response
            
            # Add delay to avoid API rate limiting
            time.sleep(0.1)
        
        # Save intermediate results every 10 rows
        if (idx + 1) % 10 == 0:
            if output_dir:
                temp_output = Path(output_dir) / "results.csv"
                df.to_csv(temp_output, index=False)
                print(f"  Saved intermediate results to {temp_output}")
            else:
                df.to_csv(OUTPUT_FILE, index=False)
                print(f"  Saved intermediate results to {OUTPUT_FILE}")
    
    # Finalize metrics
    METRICS["end_time"] = datetime.now().isoformat()
    METRICS["total_runtime_seconds"] = time.time() - start_time
    
    # Save final results
    if output_dir:
        save_metrics(output_dir, df)
    else:
        df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n✅ Processing complete!")
    print(f"   Processed {len(df)} rows")
    print(f"   Total runtime: {METRICS['total_runtime_seconds']:.2f} seconds")
    
    # Display column information
    print("\nOutput file contains the following columns:")
    for col in df.columns:
        print(f"  - {col}")
    
    return df


def main(output_dir=None):
    """Main entry point"""
    print("=" * 80)
    print("Reddit AITA LLM Comment Generator")
    print("Project: Bolun API scaling testing, 2025-11-20")
    print("=" * 80)
    
    try:
        # Verify input files exist
        if not Path(SUBMISSION_FILE).exists():
            raise FileNotFoundError(f"Submission file not found: {SUBMISSION_FILE}")
        if not Path(COMMENT_FILE).exists():
            raise FileNotFoundError(f"Comment file not found: {COMMENT_FILE}")
        
        # Process data
        df = process_data(output_dir=output_dir)
        
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

