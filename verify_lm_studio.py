
import asyncio
from openai import AsyncOpenAI

async def verify():
    print("Testing connection to LM Studio at http://localhost:1234/v1 ...")
    
    client = AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
    
    try:
        # Test 1: List models
        print("1. Listing models...")
        models = await client.models.list()
        model_ids = [m.id for m in models.data]
        print(f"   Found models: {model_ids}")
        
        target_model = "gemma-3-4b-it-qat-4bit"
        if target_model not in model_ids:
            print(f"   WARNING: Target model '{target_model}' not found in list. Proceeding anyway (might be exact match issue).")
        else:
            print(f"   Success: Found target model '{target_model}'.")

        # Test 2: Chat Completion
        print(f"2. Testing chat completion with '{target_model}'...")
        response = await client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "user", "content": "Hello! Are you working?"}
            ],
            temperature=0.7
        )
        print("   Response received:")
        print(f"   >> {response.choices[0].message.content}")
        print("\nVerification PASSED!")

    except Exception as e:
        print("\nVerification FAILED!")
        print(f"Error: {e}")
        print("Please ensure LM Studio is running and the server is started on port 1234.")

if __name__ == "__main__":
    asyncio.run(verify())
