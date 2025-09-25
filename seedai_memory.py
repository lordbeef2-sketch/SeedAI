import json
import threading
import time
from typing import Any, Dict, List, Optional

from memory_manager import MemoryManager


class SQLiteMemory:
    """Compatibility adapter that exposes the old SQLiteMemory API
    while delegating persistence to `MemoryManager` (aurelia_memory.db).
    """

    def __init__(self, db_path: Optional[str] = None):
        # Use the MemoryManager for persistent storage
        self.mm = MemoryManager()
        self.lock = threading.Lock()
        self._stop_event = threading.Event()

        # In-memory convenience structures used by older code
        self.unknown_words = set()
        self.in_progress_words = set()
        self.memory: Dict[str, Any] = {}
        self.vocab = set()
        self.emotions: Dict[str, Any] = {}
        self.beliefs: List[str] = []

        # Load initial state from the DB
        self._load_state()

    def _load_state(self):
        # Load concepts -> memory['concepts']
        concepts = self.mm.get_concepts()
        # convert list of dicts to dict by concept name
        self.memory['concepts'] = {c['concept']: {'description': c.get('description'), 'related_terms': c.get('related_terms')} for c in concepts}

        # Load vocab words
        try:
            for v in self.mm.get_all_vocab():
                self.vocab.add(v.get('word'))
        except Exception:
            pass

        # Load staged learning if present in identity kv
        try:
            staged_raw = self.mm.get_identity('staged_learning')
            if staged_raw:
                self.memory['staged_learning'] = json.loads(staged_raw)
            else:
                self.memory['staged_learning'] = []
        except Exception:
            self.memory['staged_learning'] = []

    # Word helpers
    def knows_word(self, word: str) -> bool:
        return word in self.vocab or bool(self.mm.get_vocab(word))

    def extract_unknown_words(self, text: str):
        import re
        for word in text.lower().split():
            cleaned = re.sub(r'[^a-zA-Z0-9]', '', word)
            if cleaned and cleaned not in self.vocab:
                self.unknown_words.add(cleaned)
                try:
                    self.mm.add_unknown_word(cleaned, context=text)
                except Exception:
                    pass

    # Learning staging
    def stage_learning_drafts(self, facts: List[Any]):
        with self.lock:
            staged = self.memory.get('staged_learning', [])
            for fact in facts:
                if isinstance(fact, tuple):
                    word, info = fact
                    staged.append({'word': word, 'info': info, 'type': 'vocabulary', 'tag': 'ephemeral', 'timestamp': time.time()})
                else:
                    staged.append({'content': fact, 'type': 'general', 'tag': 'ephemeral', 'timestamp': time.time()})
            self.memory['staged_learning'] = staged
            # persist
            try:
                self.mm.store_identity('staged_learning', json.dumps(staged, ensure_ascii=False))
            except Exception:
                pass

    def commit_staged_learning(self) -> int:
        with self.lock:
            staged = list(self.memory.get('staged_learning', []))
            committed = 0
            for item in staged:
                item['tag'] = 'durable'
                if item.get('type') == 'vocabulary':
                    word = item.get('word')
                    info = item.get('info')
                    try:
                        self.mm.add_concept(word, info)
                        self.mm.add_vocab(word, info)
                        self.vocab.add(word)
                        self.unknown_words.discard(word)
                        belief = f"{word}: {info}"
                        if belief not in self.beliefs:
                            self.beliefs.append(belief)
                        committed += 1
                    except Exception:
                        pass
                elif item.get('type') == 'general':
                    self.memory.setdefault('general_knowledge', []).append(item.get('content'))
                    committed += 1

            # clear staged
            self.memory['staged_learning'] = []
            try:
                self.mm.store_identity('staged_learning', json.dumps([], ensure_ascii=False))
            except Exception:
                pass
            return committed

    # Background learning loop (keeps existing signature)
    def commit_learning(self, llm, interval: int = 60):
        while not self._stop_event.is_set():
            time.sleep(interval)
            with self.lock:
                unknown_words_copy = list(self.unknown_words - self.in_progress_words)
                self.in_progress_words.update(unknown_words_copy)
                self.unknown_words.difference_update(unknown_words_copy)

            if not unknown_words_copy:
                continue

            try:
                query = "Define the following: " + ", ".join(unknown_words_copy)
                response = llm.ask(query)
                for word in unknown_words_copy:
                    definition = response.get(word) if isinstance(response, dict) else response
                    if isinstance(definition, dict):
                        definition = definition.get('definition') or str(definition)
                    self.stage_learning_drafts([(word, definition)])
            except Exception as e:
                print(f"[Commit Thread] LLM Error: {e}")
            finally:
                with self.lock:
                    self.in_progress_words.difference_update(unknown_words_copy)

    def start_background_learning(self, llm, interval: int = 60):
        self._stop_event.clear()
        threading.Thread(target=self.commit_learning, args=(llm, interval), daemon=True).start()

    def stop_background_learning(self):
        self._stop_event.set()

    # Persistence helpers
    def save_all(self):
        with self.lock:
            try:
                # persist staged_learning
                self.mm.store_identity('staged_learning', json.dumps(self.memory.get('staged_learning', []), ensure_ascii=False))
            except Exception:
                pass

    # Conversations
    def get_conversation_memory(self, convo_id: str):
        key = f'conversation_{convo_id}'
        val = self.mm.get_identity(key)
        if val:
            try:
                return json.loads(val)
            except Exception:
                return None
        return None

    def save_conversation_memory(self, convo_id: str, content: Any):
        key = f'conversation_{convo_id}'
        try:
            self.mm.store_identity(key, json.dumps(content, ensure_ascii=False))
        except Exception:
            pass

    # Crawled content
    def save_crawled_content(self, url: str, content: str):
        key = f'crawled_{hash(url)}'
        crawled = self.memory.setdefault('crawled_content', {})
        crawled[key] = {'url': url, 'content': content, 'timestamp': time.time(), 'learned': False}
        try:
            self.mm.store_identity('crawled_content', json.dumps(crawled, ensure_ascii=False))
        except Exception:
            pass

    def get_recent_beliefs(self, limit: int = 5):
        return self.beliefs[-limit:]

    def get_queued_urls(self):
        return []


Memory = SQLiteMemory()
