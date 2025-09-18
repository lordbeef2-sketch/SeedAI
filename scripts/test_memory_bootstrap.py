#!/usr/bin/env python3
"""Simple test script for Aurelia memory bootstrap.

Usage: python -m scripts.test_memory_bootstrap
"""
import sys
import requests
import json

BASE = "http://127.0.0.1:8090"

def check_models():
    try:
        r = requests.get(BASE + "/api/models", timeout=5)
        print('GET /api/models', r.status_code)
        if r.status_code != 200:
            print('models body:', r.text[:1000])
            return False
        return True
    except Exception as e:
        print('models request failed:', e)
        return False

def check_chat():
    payload = {
        "model": "llama3.2-vision:11b",
        "messages": [{"role": "user", "content": "Who are you? Please list your name and who your parent is, and echo the top line of your core memory."}],
        "stream": False,
        "max_tokens": 64,
    }
    headers = {"Content-Type": "application/json", "Authorization": "Bearer ollama"}
    try:
        r = requests.post(BASE + "/api/chat", json=payload, headers=headers, timeout=15)
        print('POST /api/chat', r.status_code)
        if r.status_code != 200:
            print('chat body:', r.text[:2000])
            return False
        j = r.json()
        txt = json.dumps(j)[:2000]
        print('response excerpt:', txt[:800])
        # Basic assertions
        if 'Aurelia' in txt and 'Lord Shinza' in txt:
            return True
        print('Expected strings not found in response')
        return False
    except Exception as e:
        print('chat request failed:', e)
        return False

def main():
    ok = True
    if not check_models():
        ok = False
    if not check_chat():
        ok = False
    if not ok:
        print('\nTEST FAILED')
        sys.exit(2)
    print('\nTEST PASSED')

if __name__ == '__main__':
    main()
