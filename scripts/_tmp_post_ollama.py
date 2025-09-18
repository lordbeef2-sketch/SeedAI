import requests
url = "http://127.0.0.1:11434/v1/chat/completions"
payload = {"model":"llama3.2-vision:11b","messages":[{"role":"user","content":"Hello Aurelia — say 'ready' if you can hear me."}],"stream":False,"max_tokens":64}
try:
    r = requests.post(url, json=payload, headers={"Authorization":"Bearer ollama"}, timeout=15)
    print(r.status_code)
    print(r.text[:2000])
except Exception as e:
    print('EXC', e)
