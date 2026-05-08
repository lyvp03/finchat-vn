"""Quick test: verify API connections for embedding + sentiment."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings
import httpx

print("=== Config Values ===")
key = settings.OPENAI_API_KEY
print(f"OPENAI_API_KEY: {key[:10]}...{key[-4:]}" if key else "OPENAI_API_KEY: (empty!)")
print(f"OPENAI_EMBEDDING_BASE_URL: {settings.OPENAI_EMBEDDING_BASE_URL}")
print(f"EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")

key2 = settings.GPT_MINI_API_KEY
print(f"GPT_MINI_API_KEY: {key2[:10]}...{key2[-4:]}" if key2 else "GPT_MINI_API_KEY: (empty!)")
print(f"GPT_MINI_BASE_URL: {settings.GPT_MINI_BASE_URL}")
print()

# --- Test 1: OpenAI Embedding ---
print("=== Test 1: OpenAI Embedding API ===")
try:
    base = settings.OPENAI_EMBEDDING_BASE_URL.rstrip("/")
    r = httpx.post(
        base + "/v1/embeddings",
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": settings.EMBEDDING_MODEL, "input": ["test connection"]},
        timeout=15.0,
    )
    if r.status_code == 200:
        data = r.json()
        dim = len(data["data"][0]["embedding"])
        print(f"  OK! Status: {r.status_code}, Dimension: {dim}")
    else:
        print(f"  FAIL! Status: {r.status_code}, Body: {r.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# --- Test 2: GPT-5-mini Sentiment ---
print("=== Test 2: GPT-5-mini Sentiment API ===")
try:
    r = httpx.post(
        settings.GPT_MINI_BASE_URL + "/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.GPT_MINI_API_KEY}"},
        json={
            "model": "GPT-5-mini",
            "messages": [{"role": "user", "content": "Say OK"}],
            "temperature": 1.0,
            "max_tokens": 5,
        },
        timeout=15.0,
    )
    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        print(f"  OK! Status: {r.status_code}, Response: {content}")
    else:
        print(f"  FAIL! Status: {r.status_code}, Body: {r.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")
