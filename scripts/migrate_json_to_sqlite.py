"""Migrate legacy JSON memory files in `seedai/memory/` into aurelia_memory.db using MemoryManager.

Run: `python scripts/migrate_json_to_sqlite.py`
"""
import json
import os
import sys
from glob import glob

# Ensure repo root is on sys.path so we can import top-level modules when running from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from memory_manager import MemoryManager

BASE = os.path.join(os.path.dirname(__file__), '..')
LEGACY_DIR = os.path.join(BASE, 'seedai', 'memory')

FILES_MAP = {
    'core.json': 'core',
    'conversations.json': 'conversations',
    'vocab.json': 'vocab',
    'emotions.json': 'emotions',
    'reflections.json': 'reflections',
    'memory_export.json': 'memory_export'
}


def load_json_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('Failed to load', path, e)
        return None


def migrate():
    mm = MemoryManager()
    try:
        # Core: identities and concepts
        core_path = os.path.join(LEGACY_DIR, 'core.json')
        if os.path.exists(core_path):
            core = load_json_file(core_path)
            if isinstance(core, dict):
                for k, v in core.items():
                    try:
                        mm.store_identity(k, json.dumps(v, ensure_ascii=False))
                    except Exception as e:
                        print('identity store failed', k, e)

                # If concepts exist in core
                concepts = core.get('concepts') or {}
                for name, data in concepts.items():
                    mm.add_concept(name, data.get('definition') or data.get('description'))
                    mm.add_vocab(name, data.get('definition') or data.get('description'))

        # Conversations
        conv_path = os.path.join(LEGACY_DIR, 'conversations.json')
        if os.path.exists(conv_path):
            conv = load_json_file(conv_path)
            if isinstance(conv, dict):
                for convo_id, messages in conv.items():
                    try:
                        mm.store_identity(f'conversation_{convo_id}', json.dumps(messages, ensure_ascii=False))
                    except Exception as e:
                        print('conv store failed', convo_id, e)

        # Vocab
        vocab_path = os.path.join(LEGACY_DIR, 'vocab.json')
        if os.path.exists(vocab_path):
            vocab = load_json_file(vocab_path)
            if isinstance(vocab, dict):
                for word, info in vocab.items():
                    mm.add_vocab(word, info if isinstance(info, str) else json.dumps(info, ensure_ascii=False))

        # Emotions
        emo_path = os.path.join(LEGACY_DIR, 'emotions.json')
        if os.path.exists(emo_path):
            emos = load_json_file(emo_path)
            if isinstance(emos, dict):
                for e, v in emos.items():
                    mm.add_emotion(e, int(v.get('value') if isinstance(v, dict) and v.get('value') else 1), json.dumps(v) if isinstance(v, dict) else None)

        # Reflections
        ref_path = os.path.join(LEGACY_DIR, 'reflections.json')
        if os.path.exists(ref_path):
            refs = load_json_file(ref_path)
            if isinstance(refs, list):
                for r in refs:
                    mm.add_reflection(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))

        print('Migration complete.')
    finally:
        mm.close()


if __name__ == '__main__':
    migrate()
