import requests
import os
import sys

from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GPT_MINI_API_KEY", "")

def test_url(url):
    print(f"Testing URL: {url}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    payload = {
        "model": "GPT-5-mini",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    base = "https://aiportalapi.stu-platform.live/use"
    test_url(base)
    test_url(f"{base}/v1/chat/completions")
    test_url(f"{base}/chat/completions")
