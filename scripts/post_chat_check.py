import requests
url = 'http://127.0.0.1:8090/api/chat'
payload = {"model":"llama3.2-vision:11b","messages":[{"role":"user","content":"hello?"}],"stream":False}
print('POST', url)
try:
    r = requests.post(url, json=payload, timeout=15)
    print('status', r.status_code)
    print(r.text)
except Exception as e:
    print('error', e)
