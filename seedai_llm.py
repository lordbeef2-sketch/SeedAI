# seedai_llm.py

"""Lightweight LLM adapter for Aurelia (uses Ollama/OpenAI-compatible APIs).

Behavior:
- Reads provider config via `gateway.providers` if available, otherwise falls back
  to `config/llm_config.json` or env vars.
- Exposes `LocalLLM` with `chat(messages, model=None, timeout=10)` that forwards
  OpenAI-compatible chat payloads to the provider's `/v1/chat/completions`.
"""

from __future__ import annotations
import os, json
from typing import List, Dict, Any, Optional

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'llm_config.json')


def _load_local_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


class LocalLLM:
    def __init__(self, model: Optional[str] = None):
        # Try to get provider info from gateway.providers when running inside the app
        try:
            from gateway import providers
            self.base = providers.get_base_url()
            self.api_key = providers.get_api_key() or os.environ.get('OLLAMA_API_KEY', '')
            self.default_model = model or providers.get_default_model() or os.environ.get('AURELIA_DEFAULT_MODEL')
        except Exception:
            cfg = _load_local_config()
            self.base = os.environ.get('OLLAMA_BASE_URL') or cfg.get('endpoint', 'http://127.0.0.1:11434')
            self.api_key = os.environ.get('OLLAMA_API_KEY') or cfg.get('api_key', '')
            self.default_model = model or cfg.get('model') or os.environ.get('AURELIA_DEFAULT_MODEL')

        # normalize base (remove trailing /v1 if present)
        if self.base.endswith('/v1'):
            self.base = self.base[:-3]

    def _build_headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def chat(self, messages: List[Dict[str, Any]], model: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
        """Send OpenAI-compatible chat messages to the provider and return provider JSON.

        messages: list of {role: string, content: string | list}
        model: optional model id to override default
        """
        target_model = model or self.default_model
        if not target_model:
            return {"error": "no_model_configured"}

        payload = {
            'model': target_model,
            'messages': [],
            'stream': False,
        }

        for m in messages:
            # support structured content (vision) or plain string
            content = m.get('content')
            if isinstance(content, list):
                payload['messages'].append({'role': m.get('role', 'user'), 'content': content})
            else:
                payload['messages'].append({'role': m.get('role', 'user'), 'content': str(content)})

        url = self.base.rstrip('/') + '/v1/chat/completions'
        try:
            import requests
            r = requests.post(url, json=payload, headers=self._build_headers(), timeout=timeout)
        except requests.exceptions.Timeout:
            return {'error': 'timeout', 'detail': f'timeout after {timeout}s'}
        except Exception as e:
            return {'error': 'provider_unreachable', 'detail': str(e)}

        try:
            data = r.json()
        except Exception:
            return {'error': 'invalid_response', 'status_code': r.status_code, 'text': r.text[:2000]}

        if r.status_code >= 200 and r.status_code < 300:
            return data
        else:
            return {'error': 'provider_error', 'status_code': r.status_code, 'provider': data}


if __name__ == '__main__':
    # quick local test when executed directly
    llm = LocalLLM()
    test = [{'role': 'user', 'content': "Hello Aurelia — say 'ready' if you can hear me."}]
    print('Using base:', llm.base)
    print('Using model:', llm.default_model)
    res = llm.chat(test, timeout=15)
    print('Result:', json.dumps(res, indent=2)[:2000])
