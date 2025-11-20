#!/usr/bin/env python3
"""Quick test script to verify Qwen model availability on OpenRouter."""
import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_model(model_id: str):
    """Test a single model with a simple request."""
    print(f"\n{'='*60}")
    print(f"Testing model: {model_id}")
    print('='*60)
    
    client = AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )
    
    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": "Say 'Hello, I am working!' in one sentence."}
            ],
            max_tokens=50
        )
        
        print(f"✅ SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
        print(f"Usage: {response.usage}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED!")
        print(f"Error: {e}")
        return False

async def main():
    """Test all Qwen model variants."""
    models_to_test = [
        "qwen/qwen-2.5-72b-instruct",  # Generic OpenRouter routing
        "fireworks/qwen2p5-72b-instruct",  # Fireworks-specific
    ]
    
    results = {}
    for model_id in models_to_test:
        success = await test_model(model_id)
        results[model_id] = success
        await asyncio.sleep(1)  # Brief pause between tests
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for model_id, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{status}: {model_id}")
    
    working_models = [m for m, s in results.items() if s]
    if working_models:
        print(f"\n🎉 Recommended model to use: {working_models[0]}")
    else:
        print("\n⚠️  No working models found!")

if __name__ == "__main__":
    asyncio.run(main())

