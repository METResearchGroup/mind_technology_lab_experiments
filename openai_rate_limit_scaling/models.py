# Models configuration
MODELS = {
    "gpt-4o-mini": "gpt-4o-mini",
    "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",  # OpenRouter generic routing (verified working)
    "llama-3.2-90b": "meta-llama/llama-3.2-90b-vision-instruct"
}

# Pricing (per 1M tokens) - Updated with web search results
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Qwen 2.5 72B on OpenRouter (generic routing, verified working)
    "qwen/qwen-2.5-72b-instruct": {"input": 0.35, "output": 0.40},
    # Llama 3.2 90B Vision on OpenRouter
    "meta-llama/llama-3.2-90b-vision-instruct": {"input": 0.90, "output": 0.90} 
}

