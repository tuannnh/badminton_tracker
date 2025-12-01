#!/usr/bin/env python3
"""Test OpenAI connection"""

import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
base_url = os.getenv('OPENAI_BASE_URL')
model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

print(f"API Key: {api_key[:20]}..." if api_key else "API Key: Not set")
print(f"Base URL: {base_url}")
print(f"Model: {model}")

if not api_key:
    print("❌ No API key configured")
    exit(1)

try:
    from openai import OpenAI
    import httpx

    http_client = httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
    )

    if base_url:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client
        )
    else:
        client = OpenAI(
            api_key=api_key,
            http_client=http_client
        )

    print("\nTesting connection...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10,
        timeout=15.0
    )

    print(f"✅ Connection successful!")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback

    traceback.print_exc()