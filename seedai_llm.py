# seedai_llm.py

import requests
import json

class LocalLLM:
    def __init__(self, config_path='config/llm_config.json'):
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.endpoint = config['endpoint']
        self.model = config['model']

    def ask(self, prompt, timeout=30):
        try:
            response = requests.post(
                self.endpoint,
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                timeout=timeout
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                return f"[Error]: Model query failed with code {response.status_code}"
        except requests.exceptions.Timeout:
            return "[Timeout]: LLM query timed out"
        except Exception as e:
            return f"[Exception]: {str(e)}"
