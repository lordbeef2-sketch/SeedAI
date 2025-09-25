import requests, json
url='http://127.0.0.1:8090/api/chat'
payload={"model":"llama3.2-vision:11b","messages":[{"role":"user","content":"Hello Aurelia — say who you are."}],"stream":False}
try:
    r=requests.post(url,json=payload,timeout=10)
    print('status',r.status_code)
    print(r.text[:4000])
except Exception as e:
    print('error',e)
