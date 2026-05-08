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

# --- Test 1: Gemini Embedding ---
print("=== Test 1: Gemini Embedding API ===")
try:
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={settings.GOOGLE_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "requests": [{"model": "models/gemini-embedding-2", "content": {"parts": [{"text": "test connection"}]}}]
        },
        timeout=15.0,
    )
    if r.status_code == 200:
        data = r.json()
        dim = len(data["embeddings"][0]["values"])
        print(f"  OK! Status: {r.status_code}, Dimension: {dim}")
    else:
        print(f"  FAIL! Status: {r.status_code}, Body: {r.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# --- Test 2: MiMo v2.5 Pro Sentiment ---
print("=== Test 2: MiMo v2.5 Pro Sentiment API ===")
try:
    r = httpx.post(
        settings.MIMO_BASE_URL + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.MIMO_API_KEY}"},
        json={
            "model": "mimo-v2.5-pro",
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
