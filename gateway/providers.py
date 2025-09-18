import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_PATH = ROOT.joinpath('provider.json')


def _load_provider_file():
    try:
        with open(PROVIDER_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def get_base_url():
    # Env overrides provider.json
    env = os.environ.get('OLLAMA_BASE_URL')
    if env:
        return env.rstrip('/')
    cfg = _load_provider_file()
    try:
        return cfg.get('providers', {}).get('ollama', {}).get('base_url', 'http://127.0.0.1:11434').rstrip('/')
    except Exception:
        return 'http://127.0.0.1:11434'


def get_api_key():
    # if api key provided in env, use it; otherwise use provider.json
    env = os.environ.get('OLLAMA_API_KEY') or os.environ.get('AURELIA_API_KEY')
    if env:
        return env
    cfg = _load_provider_file()
    try:
        return cfg.get('providers', {}).get('ollama', {}).get('api_key', '')
    except Exception:
        return ''


def get_default_model():
    env = os.environ.get('AURELIA_DEFAULT_MODEL')
    if env:
        return env
    cfg = _load_provider_file()
    try:
        return cfg.get('default_model', '')
    except Exception:
        return ''
