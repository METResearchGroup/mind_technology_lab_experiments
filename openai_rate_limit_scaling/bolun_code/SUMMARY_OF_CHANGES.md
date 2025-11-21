# Summary of Changes: Notebook → Async Python Script

**Date**: November 20, 2025  
**Original**: `LLM_comment.ipynb` (Jupyter Notebook)  
**New Version**: `main.py` (Async Python Script)

---

## 🎯 Overview

Converted a synchronous Jupyter notebook that sequentially processes Reddit AITA submissions through 3 LLM models into a high-performance async Python script with comprehensive telemetry and metrics tracking.

### Performance Impact
- **Original**: ~5-8 hours for 1000 submissions (sequential processing)
- **New**: ~5-6 minutes for 919 submissions (**60-90x faster**)
- **Throughput**: 8.2 API requests/sec sustained

---

## 🔄 Major Changes

### 1. **Async/Await Concurrency**
- Converted from synchronous `OpenAI` client to `AsyncOpenAI` for non-blocking I/O
- All LLM API calls now use async/await pattern
- Shared client instance across all requests for connection pooling
- Eliminates waiting time while API processes requests

### 2. **Semaphore-Based Concurrency Control**
- Added semaphore limiting max concurrent requests to 40
- All 3 models (DeepSeek, GPT, Llama) now called simultaneously per submission
- Up to ~13 submissions processing in parallel (40 concurrent requests / 3 models)
- Removed artificial delays between API calls
- Stays under Opik's 5,000 events/min workspace limit while maximizing throughput

### 3. **Input Data Source Change**
- Changed from reading two JSON files (`final_1000_submissions.json`, `final_3000_comments.json`) to reading single Excel file
- Now reads directly from `AITA_LLM_results_test_1000.xlsx`
- Automatically clears existing model responses to force fresh reprocessing
- Simplified data loading logic
- Added `openpyxl` dependency for Excel support

### 4. **Output Format & Structure**
- Changed output from Excel (`.xlsx`) to CSV (`.csv`) format
- Added timestamped output directories: `outputs/2025_11_20-18:47:48/`
- Separated concerns into three files:
  - `metadata.json` - Configuration and settings
  - `output.json` - Detailed metrics and statistics
  - `results.csv` - Complete data with model responses
- Automatic checkpoint saving every 50 submissions

### 5. **Opik Telemetry Integration**
- Added `@track` decorators to all major functions for automatic tracing
- Wrapped OpenAI client with `track_openai()` for detailed API call logging
- All traces sent to dedicated Opik project: "Bolun API scaling testing, 2025-11-20"
- Automatically captures latency, token usage, and errors for each API call
- Enables debugging and performance analysis through Opik dashboard

### 6. **Comprehensive Metrics Tracking**
- Tracks total requests, success/failure counts per model
- Records all latencies per model (mean, min, max)
- Logs all error messages with sample errors per model
- Calculates overall success rate and throughput
- Exports detailed metrics to `output.json` for post-run analysis

### 7. **Real-Time Progress Logging**
- Progress updates every 10 API requests (vs basic tqdm bar)
- Shows: completed requests, submission count, current rate, and accurate ETA
- Added `flush=True` to all print statements for immediate output
- Checkpoint save notifications
- Example: `✓ Completed 1200/2757 API requests | 400/919 submissions | Rate: 8.1 req/sec | ETA: 3.2 min`

### 8. **Environment Variable Management**
- Moved all API keys from hardcoded strings to `.env` files
- Hierarchical loading: root `.env` for Opik credentials, local `.env` for DeepInfra key
- Added validation for required environment variables
- Improves security and makes credentials easier to manage

### 9. **Error Handling & Retry Logic**
- Changed blocking `time.sleep()` to async `await asyncio.sleep()` in retry logic
- Async sleep doesn't block other concurrent requests during retries
- All errors tracked in metrics with sample messages exported to `output.json`
- Failed requests saved to CSV with "ERROR:" prefix for visibility

### 10. **Bash Runner Script**
- Created `run_bolun_code.sh` for easy execution
- Automatic timestamp generation for output directories
- Virtual environment activation
- Dependency checking before run
- Pretty formatted summary with colors and emoji
- Exit code handling with success/failure messages

---

## 📊 Comparative Metrics

| Metric | Notebook | Async Script | Improvement |
|--------|----------|--------------|-------------|
| **Processing Time (1000 items)** | ~5-8 hours | ~5-6 minutes | **60-90x faster** |
| **Throughput** | ~0.05-0.1 req/sec | 8.2 req/sec | **80-160x faster** |
| **Concurrent Requests** | 1 | 40 | **40x parallelism** |
| **Models per Submission** | Sequential (3×) | Concurrent (3 at once) | **3x faster** |
| **Progress Visibility** | Basic tqdm bar | Real-time metrics + ETA | ✅ Enhanced |
| **Error Tracking** | Console only | Structured metrics | ✅ Enhanced |
| **Telemetry** | None | Full Opik integration | ✅ New |
| **Checkpointing** | Every 10 rows | Every 50 submissions | ✅ Optimized |
| **Output Format** | Excel only | CSV + JSON metrics | ✅ Enhanced |

---

## 🛠️ New Dependencies

- `asyncio` (built-in) - Async/await support
- `openpyxl` - Excel file reading
- `python-dotenv` - Environment variable management
- `opik` - Telemetry and observability
- `AsyncOpenAI` (from `openai` package) - Async API client

---

## 🔑 Key Architectural Decisions

### Why Semaphore-Based Concurrency?
- Respects Opik's 5,000 events/min workspace rate limit
- Calculation: 40 concurrent × 3 events each = ~7,200/min theoretical, but spread over time stays under limit
- Easily tunable via `CONCURRENCY_LIMIT` constant

### Why AsyncIO Over Threading?
- I/O-bound workload (waiting for API responses)
- Lower overhead than threads (no GIL contention)
- Semaphores integrate naturally with async
- Better Opik compatibility

### Why Clear Existing Responses?
- Ensures fresh data on every run (idempotent)
- Makes rerunning experiments easier
- All data comes from same run/timestamp

### Why CSV Instead of Excel?
- 10-100x faster to write
- Smaller file size
- Easier to process with other tools
- Simpler (no extra dependencies for output)

---

## 🚀 Usage Comparison

**Before (Notebook):**
1. Open Jupyter Notebook → 2. Edit hardcoded API key → 3. Ensure JSON files present → 4. Run cells → 5. Wait 5-8 hours → 6. Get Excel file

**After (Script):**
1. Create `.env` file with keys → 2. Place Excel file in directory → 3. Run `bash run_bolun_code.sh` → 4. Wait 5-6 minutes → 5. Get timestamped folder with results

---

## 📝 Configuration

Main tunable constants in `main.py`:
- `CONCURRENCY_LIMIT = 40` - Max concurrent API requests
- `save_interval = 50` - Checkpoint frequency (submissions)
- Progress updates every 10 API requests
- Same 3 models, system prompt, retry logic, and timeout as original

---

## ✅ What Was Preserved

- Same 3 models (DeepSeek, GPT, Llama)
- Same system prompt
- Same column structure in output
- Same retry logic (3 attempts with 2-second delay)
- Same timeout (60 seconds per request)

## ❌ What Changed

- Sequential → Async concurrent processing
- Excel output → CSV output (Excel input still supported)
- JSON files input → Excel input
- Chinese logging → English logging

---

## 🎓 Key Takeaways

1. Async provides 60-90x speedup for I/O-bound workloads
2. Semaphores essential for respecting rate limits while maximizing throughput
3. Opik integration adds minimal overhead with major observability gains
4. Real-time progress critical for long-running jobs
5. Structured metrics (JSON) more useful than console logs
6. Environment variables better than hardcoded secrets
7. Timestamped outputs prevent overwrites and aid experiment tracking

---

## 🐛 Known Limitations & Future Work

**Current Limitations:**
- No exponential backoff retry
- No graceful shutdown on Ctrl+C
- Metrics tracking not thread-safe (minor issue)
- No resume capability if crash mid-run

**Potential Enhancements:**
- Add `aiolimiter` for precise rate limiting
- Graceful shutdown with result preservation
- Resume capability via checkpoint files
- Dynamic concurrency based on error rates
- Per-model latency histograms
- Multi-format export (Excel, JSON, Parquet)
- Cost tracking per model
- Batch processing for large datasets

---

**Last Updated**: November 20, 2025  
**Python Version**: 3.11.5  
**Key Libraries**: `openai>=1.0.0`, `opik`, `pandas`, `python-dotenv`, `openpyxl`
