#!/usr/bin/env python
"""scripts/test_gateway_chat.py

Performs quick checks against the local gateway:
- GET /api/models
- POST /api/chat
- GET /healthz

Prints status codes and first 800 chars of the responses.
"""
import json
import sys
from urllib import request, parse

BASE = "http://127.0.0.1:8090"

def get(path):
    url = BASE + path
    try:
        req = request.Request(url, headers={"User-Agent": "Aurelia-Test/1.0"})
        with request.urlopen(req, timeout=10) as f:
            return f.getcode(), f.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, str(e)

def post(path, data):
    url = BASE + path
    try:
        body = json.dumps(data).encode('utf-8')
        req = request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=15) as f:
            return f.getcode(), f.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, str(e)

def short(s, n=800):
    return (s[:n] + '...') if s and len(s) > n else s

def main():
    print("[TEST] GET /healthz")
    code, body = get("/healthz")
    print(code, short(body))

    print("[TEST] GET /api/models")
    code, body = get("/api/models")
    print(code, short(body))

    print("[TEST] POST /api/chat")
    payload = {
        "model": "llama3.2-vision:11b",
        "messages": [{"role": "user", "content": "Hello Aurelia — say 'ready' if you can hear me."}],
        "stream": False,
        "max_tokens": 64
    }
    code, body = post("/api/chat", payload)
    print(code, short(body))

if __name__ == '__main__':
    main()
