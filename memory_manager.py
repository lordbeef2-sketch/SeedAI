import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Any, Dict
import time
import os
import json
import re
import requests
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser


DEFAULT_DB_PATH = 'aurelia_memory.db'
MAX_CONTENT_BYTES = 2 * 1024 * 1024  # 2MB


class AureliaError(Exception):
    pass


def _redact_key(key: str) -> str:
    if not key:
        return ''
    if len(key) <= 8:
        return '****' + key[-4:]
    return key[:4] + '****' + key[-4:]


def with_retry(fn):
    """Decorator to retry sqlite busy/locked errors with exponential backoff (total ~1s)."""

    def wrapper(self, *args, **kwargs):
        delays = [0.01, 0.02, 0.05, 0.1, 0.2, 0.4]
        last_exc = None
        for wait in delays:
            try:
                return fn(self, *args, **kwargs)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if 'database is locked' in msg or 'database table is locked' in msg or 'locked' in msg:
                    last_exc = e
                    time.sleep(wait)
                    continue
                raise
        # final attempt
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            if last_exc:
                raise AureliaError(f'SQLite busy: {last_exc}') from last_exc
            raise

    return wrapper


class _SimpleHTMLParser(HTMLParser):
    def __init__(self, base_url: str = ''):
        super().__init__()
        self._texts = []
        self._links = []
        self._in_ignored = False
        self.base = base_url

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._in_ignored = True
        if tag == 'a':
            href = None
            for k, v in attrs:
                if k == 'href':
                    href = v
                    break
            if href:
                try:
                    abs_url = urljoin(self.base, href)
                    self._links.append(abs_url)
                except Exception:
                    pass

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._in_ignored = False

    def handle_data(self, data):
        if self._in_ignored:
            return
        text = data.strip()
        if text:
            self._texts.append(text)

    def get_text(self):
        return ' '.join(self._texts)

    def get_links(self):
        return self._links


class MemoryManager:
    """Production-ready SQLite-backed memory manager with crawling, codegen, FTS, and performance tuning."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, timeout: float = 30.0):
        self.db_path = db_path
        self.timeout = timeout
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        with self._lock:
            if self._conn:
                return
            self._conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Performance pragmas
            cur = self._conn.cursor()
            cur.execute('PRAGMA foreign_keys = ON')
            cur.execute('PRAGMA journal_mode = WAL')
            cur.execute('PRAGMA synchronous = NORMAL')
            cur.execute('PRAGMA temp_store = MEMORY')
            cur.execute('PRAGMA mmap_size = 268435456')
            cur.execute('PRAGMA cache_size = -20000')
            self._ensure_tables_and_migrations()

    def close(self):
        with self._lock:
            if self._conn:
                try:
                    self._conn.commit()
                except Exception:
                    pass
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    @contextmanager
    def _transaction(self):
        if not self._conn:
            self._connect()
        cur = self._conn.cursor()
        try:
            cur.execute('BEGIN')
            yield cur
            cur.execute('COMMIT')
        except Exception:
            try:
                cur.execute('ROLLBACK')
            except Exception:
                pass
            raise

    def _ensure_tables_and_migrations(self):
        cur = self._conn.cursor()
        # Base tables
        base_sql = [
            (
                "identity",
                """
                CREATE TABLE IF NOT EXISTS identity (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """,
            ),
            ("relationships", """
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY,
                    type TEXT,
                    target TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("capabilities", """
                CREATE TABLE IF NOT EXISTS capabilities (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    learned_on DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("principles", """
                CREATE TABLE IF NOT EXISTS principles (
                    id INTEGER PRIMARY KEY,
                    text TEXT,
                    source TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("vocab", """
                CREATE TABLE IF NOT EXISTS vocab (
                    word TEXT PRIMARY KEY,
                    definition TEXT,
                    examples TEXT,
                    learned_on DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("unknown_words", """
                CREATE TABLE IF NOT EXISTS unknown_words (
                    word TEXT PRIMARY KEY,
                    context TEXT,
                    first_seen DATETIME,
                    resolved BOOLEAN DEFAULT 0
                )
            """),
            ("grammar_rules", """
                CREATE TABLE IF NOT EXISTS grammar_rules (
                    id INTEGER PRIMARY KEY,
                    rule TEXT,
                    example TEXT,
                    learned_on DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("memories", """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    type TEXT,
                    content TEXT,
                    emotion TEXT,
                    importance INTEGER DEFAULT 1,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("reflections", """
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY,
                    thought TEXT,
                    tone TEXT,
                    cause TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("sessions", """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at DATETIME,
                    ended_at DATETIME,
                    notes TEXT
                )
            """),
            ("emotions", """
                CREATE TABLE IF NOT EXISTS emotions (
                    id INTEGER PRIMARY KEY,
                    emotion TEXT,
                    intensity INTEGER,
                    trigger TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("mood_history", """
                CREATE TABLE IF NOT EXISTS mood_history (
                    id INTEGER PRIMARY KEY,
                    mood TEXT,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("questions", """
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY,
                    question TEXT,
                    status TEXT,
                    answer TEXT,
                    source TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("goals", """
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY,
                    goal TEXT,
                    priority INTEGER,
                    status TEXT,
                    created_on DATETIME,
                    updated_on DATETIME
                )
            """),
            ("tasks", """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    task TEXT,
                    context TEXT,
                    status TEXT,
                    due_date DATETIME,
                    completed_on DATETIME
                )
            """),
            ("skills", """
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY,
                    skill TEXT,
                    proficiency INTEGER,
                    practice_notes TEXT,
                    last_practiced DATETIME
                )
            """),
            ("facts", """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY,
                    subject TEXT,
                    predicate TEXT,
                    object TEXT,
                    source TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("concepts", """
                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY,
                    concept TEXT,
                    description TEXT,
                    related_terms TEXT,
                    learned_on DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("knowledge_links", """
                CREATE TABLE IF NOT EXISTS knowledge_links (
                    id INTEGER PRIMARY KEY,
                    concept_a TEXT,
                    concept_b TEXT,
                    relation_type TEXT
                )
            """),
            ("system_logs", """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY,
                    event TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("errors", """
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY,
                    error_text TEXT,
                    context TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("updates", """
                CREATE TABLE IF NOT EXISTS updates (
                    id INTEGER PRIMARY KEY,
                    change TEXT,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            # New tables per Phase 2
            ("crawls", """
                CREATE TABLE IF NOT EXISTS crawls (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE,
                    title TEXT,
                    content TEXT,
                    links TEXT,
                    crawled_on DATETIME DEFAULT CURRENT_TIMESTAMP,
                    approved_by TEXT CHECK(approved_by IN ('Father','Mother'))
                )
            """),
            ("api_keys", """
                CREATE TABLE IF NOT EXISTS api_keys (
                    service TEXT PRIMARY KEY,
                    key TEXT,
                    added_on DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ("schema_migrations", """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_on DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """),
        ]

        for name, stmt in base_sql:
            cur.execute(stmt)

        # Indexes
        idxs = [
            'CREATE INDEX IF NOT EXISTS idx_memories_type_ts ON memories(type, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)',
            'CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocab(word)',
            'CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject)',
            'CREATE INDEX IF NOT EXISTS idx_facts_predicate ON facts(predicate)',
            'CREATE INDEX IF NOT EXISTS idx_facts_object ON facts(object)',
            'CREATE INDEX IF NOT EXISTS idx_concepts_concept ON concepts(concept)',
            'CREATE INDEX IF NOT EXISTS idx_crawls_url ON crawls(url)',
            'CREATE INDEX IF NOT EXISTS idx_updates_ts ON updates(timestamp)'
        ]
        for s in idxs:
            try:
                cur.execute(s)
            except Exception:
                pass

        # FTS5 setup (best-effort)
        try:
            cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_memories USING fts5(content, emotion, type, content='memories', content_rowid='id')")
            cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_crawls USING fts5(content, title, url, content='crawls', content_rowid='id')")
            cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_vocab USING fts5(definition, examples, word, content='vocab', content_rowid='rowid')")

            # triggers for memories
            cur.executescript(r"""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO fts_memories(rowid, content, emotion, type) VALUES (new.id, new.content, new.emotion, new.type);
            END;
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO fts_memories(fts_memories, rowid, content, emotion, type) VALUES('delete', old.id, old.content, old.emotion, old.type);
            END;
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO fts_memories(fts_memories, rowid, content, emotion, type) VALUES('delete', old.id, old.content, old.emotion, old.type);
                INSERT INTO fts_memories(rowid, content, emotion, type) VALUES (new.id, new.content, new.emotion, new.type);
            END;

            -- crawls
            CREATE TRIGGER IF NOT EXISTS crawls_ai AFTER INSERT ON crawls BEGIN
                INSERT INTO fts_crawls(rowid, content, title, url) VALUES (new.id, new.content, new.title, new.url);
            END;
            CREATE TRIGGER IF NOT EXISTS crawls_ad AFTER DELETE ON crawls BEGIN
                INSERT INTO fts_crawls(fts_crawls, rowid, content, title, url) VALUES('delete', old.id, old.content, old.title, old.url);
            END;
            CREATE TRIGGER IF NOT EXISTS crawls_au AFTER UPDATE ON crawls BEGIN
                INSERT INTO fts_crawls(fts_crawls, rowid, content, title, url) VALUES('delete', old.id, old.content, old.title, old.url);
                INSERT INTO fts_crawls(rowid, content, title, url) VALUES (new.id, new.content, new.title, new.url);
            END;

            -- vocab (uses rowid)
            CREATE TRIGGER IF NOT EXISTS vocab_ai AFTER INSERT ON vocab BEGIN
                INSERT INTO fts_vocab(rowid, definition, examples, word) VALUES (new.rowid, new.definition, new.examples, new.word);
            END;
            CREATE TRIGGER IF NOT EXISTS vocab_ad AFTER DELETE ON vocab BEGIN
                INSERT INTO fts_vocab(fts_vocab, rowid, definition, examples, word) VALUES('delete', old.rowid, old.definition, old.examples, old.word);
            END;
            CREATE TRIGGER IF NOT EXISTS vocab_au AFTER UPDATE ON vocab BEGIN
                INSERT INTO fts_vocab(fts_vocab, rowid, definition, examples, word) VALUES('delete', old.rowid, old.definition, old.examples, old.word);
                INSERT INTO fts_vocab(rowid, definition, examples, word) VALUES (new.rowid, new.definition, new.examples, new.word);
            END;
            """)
        except Exception:
            # FTS5 not available or triggers failed; ignore but continue
            pass

        self._conn.commit()

    # Identity
    @with_retry
    def store_identity(self, key: str, value: str):
        if not key:
            raise AureliaError('identity key required')
        if value is None:
            value = ''
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('REPLACE INTO identity(key, value) VALUES(?, ?)', (key, str(value)))

    def get_identity(self, key: str) -> Optional[str]:
        if not self._conn:
            self._connect()
        cur = self._conn.cursor()
        cur.execute('SELECT value FROM identity WHERE key = ?', (key,))
        row = cur.fetchone()
        return row['value'] if row else None

    # Relationships
    @with_retry
    def add_relationship(self, type: str, target: str, details: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO relationships(type, target, details) VALUES(?, ?, ?)', (type, target, details))
                return cur.lastrowid

    def get_relationships(self, type: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        if type:
            cur.execute('SELECT * FROM relationships WHERE type = ? ORDER BY timestamp DESC', (type,))
        else:
            cur.execute('SELECT * FROM relationships ORDER BY timestamp DESC')
        return [dict(r) for r in cur.fetchall()]

    # Capabilities
    @with_retry
    def add_capability(self, name: str, description: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO capabilities(name, description) VALUES(?, ?)', (name, description))
                return cur.lastrowid

    def list_capabilities(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM capabilities ORDER BY learned_on DESC')
        return [dict(r) for r in cur.fetchall()]

    # Principles
    @with_retry
    def add_principle(self, text: str, source: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO principles(text, source) VALUES(?, ?)', (text, source))
                return cur.lastrowid

    def list_principles(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM principles ORDER BY timestamp DESC')
        return [dict(r) for r in cur.fetchall()]

    # Vocab
    @with_retry
    def add_vocab(self, word: str, definition: str, examples: Optional[str] = None):
        if not word:
            raise AureliaError('word required')
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('REPLACE INTO vocab(word, definition, examples) VALUES(?, ?, ?)', (word, definition, examples))

    def get_vocab(self, word: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM vocab WHERE word = ?', (word,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_vocab(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM vocab ORDER BY learned_on DESC')
        return [dict(r) for r in cur.fetchall()]

    # Unknown words
    @with_retry
    def add_unknown_word(self, word: str, context: Optional[str] = None):
        if not word:
            return
        now = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT OR IGNORE INTO unknown_words(word, context, first_seen, resolved) VALUES(?, ?, ?, 0)', (word, context, now))

    @with_retry
    def resolve_unknown_word(self, word: str, definition: str, examples: Optional[str] = None):
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('REPLACE INTO vocab(word, definition, examples) VALUES(?, ?, ?)', (word, definition, examples))
                cur.execute('UPDATE unknown_words SET resolved = 1 WHERE word = ?', (word,))

    # Grammar rules
    @with_retry
    def add_grammar_rule(self, rule: str, example: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO grammar_rules(rule, example) VALUES(?, ?)', (rule, example))
                return cur.lastrowid

    def list_grammar_rules(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM grammar_rules ORDER BY learned_on DESC')
        return [dict(r) for r in cur.fetchall()]

    # Memories
    @with_retry
    def add_memory(self, type: str, content: str, emotion: Optional[str] = None, importance: int = 1) -> int:
        if content is None:
            content = ''
        if len(content.encode('utf-8')) > MAX_CONTENT_BYTES:
            content = content.encode('utf-8')[:MAX_CONTENT_BYTES].decode('utf-8', errors='ignore')
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO memories(type, content, emotion, importance) VALUES(?, ?, ?, ?)', (type, content, emotion, importance))
                return cur.lastrowid

    def get_memories(self, type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        if type:
            cur.execute('SELECT * FROM memories WHERE type = ? ORDER BY timestamp DESC LIMIT ?', (type, limit))
        else:
            cur.execute('SELECT * FROM memories ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(r) for r in cur.fetchall()]

    # Reflections
    @with_retry
    def add_reflection(self, thought: str, tone: Optional[str] = None, cause: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO reflections(thought, tone, cause) VALUES(?, ?, ?)', (thought, tone, cause))
                return cur.lastrowid

    def get_reflections(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM reflections ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(r) for r in cur.fetchall()]

    # Sessions
    @with_retry
    def start_session(self, session_id: str, notes: Optional[str] = None):
        now = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT OR REPLACE INTO sessions(session_id, started_at, ended_at, notes) VALUES(?, ?, NULL, ?)', (session_id, now, notes))

    @with_retry
    def end_session(self, session_id: str, notes: Optional[str] = None):
        now = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('UPDATE sessions SET ended_at = ?, notes = COALESCE(notes, "") || ? WHERE session_id = ?', (now, '\n' + (notes or ''), session_id))

    # Emotions
    @with_retry
    def add_emotion(self, emotion: str, intensity: int = 1, trigger: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO emotions(emotion, intensity, trigger) VALUES(?, ?, ?)', (emotion, intensity, trigger))
                return cur.lastrowid

    def get_emotions(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM emotions ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(r) for r in cur.fetchall()]

    # Mood history
    @with_retry
    def add_mood(self, mood: str, reason: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO mood_history(mood, reason) VALUES(?, ?)', (mood, reason))
                return cur.lastrowid

    def get_mood_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM mood_history ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(r) for r in cur.fetchall()]

    # Questions
    @with_retry
    def add_question(self, question: str, source: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO questions(question, status, source) VALUES(?, ?, ?)', (question, 'open', source))
                return cur.lastrowid

    @with_retry
    def update_question(self, id: int, answer: Optional[str] = None, status: Optional[str] = None):
        with self._write_lock:
            with self._transaction() as cur:
                if answer is not None and status is not None:
                    cur.execute('UPDATE questions SET answer = ?, status = ? WHERE id = ?', (answer, status, id))
                elif answer is not None:
                    cur.execute('UPDATE questions SET answer = ? WHERE id = ?', (answer, id))
                elif status is not None:
                    cur.execute('UPDATE questions SET status = ? WHERE id = ?', (status, id))

    # Goals
    @with_retry
    def add_goal(self, goal: str, priority: int = 1) -> int:
        now = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO goals(goal, priority, status, created_on, updated_on) VALUES(?, ?, ?, ?, ?)', (goal, priority, 'open', now, now))
                return cur.lastrowid

    @with_retry
    def update_goal(self, id: int, status: str):
        now = datetime.utcnow().isoformat()
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('UPDATE goals SET status = ?, updated_on = ? WHERE id = ?', (status, now, id))

    def list_goals(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM goals ORDER BY created_on DESC')
        return [dict(r) for r in cur.fetchall()]

    # Tasks
    @with_retry
    def add_task(self, task: str, context: Optional[str] = None, due_date: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO tasks(task, context, status, due_date) VALUES(?, ?, ?, ?)', (task, context, 'open', due_date))
                return cur.lastrowid

    @with_retry
    def update_task(self, id: int, status: Optional[str] = None):
        with self._write_lock:
            with self._transaction() as cur:
                if status is not None:
                    if status.lower() in ('completed', 'done'):
                        now = datetime.utcnow().isoformat()
                        cur.execute('UPDATE tasks SET status = ?, completed_on = ? WHERE id = ?', (status, now, id))
                    else:
                        cur.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, id))

    def list_tasks(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM tasks ORDER BY due_date IS NULL, due_date ASC')
        return [dict(r) for r in cur.fetchall()]

    # Skills
    @with_retry
    def add_skill(self, skill: str, proficiency: int = 1, practice_notes: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO skills(skill, proficiency, practice_notes, last_practiced) VALUES(?, ?, ?, ?)', (skill, proficiency, practice_notes, datetime.utcnow().isoformat()))
                return cur.lastrowid

    @with_retry
    def update_skill(self, id: int, proficiency: int):
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('UPDATE skills SET proficiency = ?, last_practiced = ? WHERE id = ?', (proficiency, datetime.utcnow().isoformat(), id))

    def list_skills(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM skills ORDER BY last_practiced DESC')
        return [dict(r) for r in cur.fetchall()]

    # Facts
    @with_retry
    def add_fact(self, subject: str, predicate: str, object: str, source: Optional[str] = None) -> int:
        if subject is None:
            raise AureliaError('subject required')
        if object is None:
            object = ''
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO facts(subject, predicate, object, source) VALUES(?, ?, ?, ?)', (subject, predicate, object, source))
                return cur.lastrowid

    def get_facts(self, subject: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        if subject:
            cur.execute('SELECT * FROM facts WHERE subject = ? ORDER BY timestamp DESC', (subject,))
        else:
            cur.execute('SELECT * FROM facts ORDER BY timestamp DESC')
        return [dict(r) for r in cur.fetchall()]

    # Concepts
    @with_retry
    def add_concept(self, concept: str, description: Optional[str] = None, related_terms: Optional[str] = None) -> int:
        if not concept:
            raise AureliaError('concept required')
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO concepts(concept, description, related_terms) VALUES(?, ?, ?)', (concept, description, related_terms))
                return cur.lastrowid

    def get_concepts(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM concepts ORDER BY learned_on DESC')
        return [dict(r) for r in cur.fetchall()]

    @with_retry
    def link_concepts(self, concept_a: str, concept_b: str, relation_type: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO knowledge_links(concept_a, concept_b, relation_type) VALUES(?, ?, ?)', (concept_a, concept_b, relation_type))
                return cur.lastrowid

    def get_links(self, concept: str) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM knowledge_links WHERE concept_a = ? OR concept_b = ?', (concept, concept))
        return [dict(r) for r in cur.fetchall()]

    # System logs
    @with_retry
    def log_event(self, event: str, details: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO system_logs(event, details) VALUES(?, ?)', (event, details))
                return cur.lastrowid

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(r) for r in cur.fetchall()]

    # Errors
    @with_retry
    def log_error(self, error_text: str, context: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO errors(error_text, context) VALUES(?, ?)', (error_text, context))
                return cur.lastrowid

    @with_retry
    def resolve_error(self, id: int):
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (id,))

    def get_errors(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM errors ORDER BY timestamp DESC')
        return [dict(r) for r in cur.fetchall()]

    # Updates
    @with_retry
    def record_update(self, change: str, reason: Optional[str] = None) -> int:
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT INTO updates(change, reason) VALUES(?, ?)', (change, reason))
                return cur.lastrowid

    def get_updates(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM updates ORDER BY timestamp DESC')
        return [dict(r) for r in cur.fetchall()]

    # Crawling (parent-gated)
    def _sanitize_url(self, url: str) -> str:
        if not url:
            raise AureliaError('url required')
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'http://' + url
            parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise AureliaError('unsupported url scheme')
        return url

    @with_retry
    def crawl_url(self, url: str, approved_by: str) -> Dict[str, Any]:
        if approved_by not in ('Father', 'Mother'):
            raise AureliaError('crawl must be approved by Father or Mother')
        url = self._sanitize_url(url)

        # Fetch
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            raise AureliaError(f'fetch failed: {e}')

        parser = _SimpleHTMLParser(base_url=url)
        try:
            parser.feed(html)
            parser.close()
        except Exception:
            # fall back: minimal text
            pass

        title = ''
        # try to extract <title>
        m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()
        if not title:
            # fallback to hostname
            try:
                title = urlparse(url).hostname or url
            except Exception:
                title = url

        content = parser.get_text()[:MAX_CONTENT_BYTES]
        links = parser.get_links()
        links_json = json.dumps(links, ensure_ascii=False)

        # store crawl
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('INSERT OR REPLACE INTO crawls(url, title, content, links, approved_by) VALUES(?, ?, ?, ?, ?)', (url, title, content, links_json, approved_by))
                # get id
                cur.execute('SELECT id, crawled_on FROM crawls WHERE url = ?', (url,))
                row = cur.fetchone()
                crawled_on = row['crawled_on'] if row else datetime.utcnow().isoformat()

        # derived knowledge
        first_200 = content[:200]
        try:
            self.add_fact(url, 'contains_text', first_200, source=url)
        except Exception:
            pass

        # summary: naive first 1-2 sentences
        summary = ''
        sentences = re.split(r'[\.\n]\s*', content)
        if sentences:
            summary = '. '.join(s for s in sentences[:2] if s).strip()

        # top link hostnames
        hosts = {}
        for l in links:
            try:
                h = urlparse(l).hostname
                if h:
                    hosts[h] = hosts.get(h, 0) + 1
            except Exception:
                pass
        top_hosts = sorted(hosts.items(), key=lambda x: -x[1])[:5]
        related = ','.join(h for h, _ in top_hosts)
        try:
            concept_name = title or urlparse(url).hostname or url
            self.add_concept(concept_name, description=summary, related_terms=related)
        except Exception:
            pass

        try:
            self.log_event('crawl', f'url={url}; title={title}')
        except Exception:
            pass

        return {'url': url, 'title': title, 'words': len(content.split()), 'links_count': len(links), 'crawled_on': crawled_on}

    def get_crawl_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM crawls WHERE url = ?', (url,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_crawls(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM crawls ORDER BY crawled_on DESC LIMIT ?', (limit,))
        return [dict(r) for r in cur.fetchall()]

    # API keys
    @with_retry
    def add_api_key(self, service: str, key: str):
        if not service or not key:
            raise AureliaError('service and key required')
        with self._write_lock:
            with self._transaction() as cur:
                cur.execute('REPLACE INTO api_keys(service, key) VALUES(?, ?)', (service, key))

    def get_api_key(self, service: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute('SELECT key FROM api_keys WHERE service = ?', (service,))
        row = cur.fetchone()
        return row['key'] if row else None

    def list_api_keys(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT service, added_on FROM api_keys ORDER BY added_on DESC')
        return [dict(r) for r in cur.fetchall()]

    # Code generation (self-coding) - no auto-exec
    @with_retry
    def generate_code(self, prompt: str, service: str = 'gpt-5-mini', filename_prefix: str = 'gen') -> Dict[str, Any]:
        if not prompt:
            raise AureliaError('prompt required')
        key = self.get_api_key(service)
        if not key:
            raise AureliaError('api key missing for service')

        created_on = datetime.utcnow().isoformat()
        gen_dir = os.path.join(os.getcwd(), 'generated')
        os.makedirs(gen_dir, exist_ok=True)

        if service == 'gpt-5-mini':
            url = os.getenv('AURELIA_GEN_URL', 'http://127.0.0.1:11434/v1/chat')
            model = os.getenv('AURELIA_GEN_MODEL', 'gpt-5-mini')
            body = {'model': model, 'messages': [{'role': 'system', 'content': "You are Aurelia\'s coder."}, {'role': 'user', 'content': prompt}], 'temperature': 0.2}
            headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                raise AureliaError(f'codegen request failed: {e}')

            # best-effort extraction
            code_text = ''
            # common shapes: choices -> message -> content
            if isinstance(data, dict):
                # try common patterns
                for k in ('choices', 'outputs', 'result'):
                    if k in data and isinstance(data[k], list):
                        for item in data[k]:
                            # try several nested paths
                            if isinstance(item, dict):
                                for p in ('message', 'content', 'text'):
                                    v = item.get(p)
                                    if isinstance(v, str) and v.strip():
                                        code_text = v
                                        break
                            if code_text:
                                break
                    if code_text:
                        break
                if not code_text:
                    # try top-level content
                    for p in ('content', 'text'):
                        if p in data and isinstance(data[p], str):
                            code_text = data[p]
                            break

        elif service == 'ollama':
            model = os.getenv('AURELIA_OLLAMA_MODEL', 'llama3')
            url = os.getenv('AURELIA_OLLAMA_URL', 'http://127.0.0.1:11434/api/generate')
            body = {'model': model, 'prompt': prompt, 'options': {'temperature': 0.2}}
            try:
                resp = requests.post(url, json=body, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                raise AureliaError(f'ollama request failed: {e}')

            code_text = ''
            if isinstance(data, dict):
                # look for 'response' or 'text'
                for p in ('response', 'text', 'output'):
                    if p in data and isinstance(data[p], str):
                        code_text = data[p]
                        break
        else:
            raise AureliaError('unsupported service')

        # fallback raw
        if not code_text and isinstance(data, str):
            code_text = data

        if not code_text and isinstance(data, dict):
            # try to stringify
            code_text = json.dumps(data, ensure_ascii=False)

        # Prefer fenced code blocks
        m = re.search(r'```(?:python\n)?([\s\S]*?)```', code_text)
        if m:
            final_code = m.group(1).strip()
        else:
            final_code = code_text.strip()

        if not final_code:
            raise AureliaError('no code returned')

        ts = int(time.time())
        fname = f"{ts}_{filename_prefix}.py"
        path = os.path.join(gen_dir, fname)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(final_code)
        except Exception as e:
            raise AureliaError(f'failed saving code: {e}')

        try:
            self.record_update('code_generated', 'self-code')
            self.log_event('codegen', f'service={service}; file={path}')
        except Exception:
            pass

        size = os.path.getsize(path)
        return {'service': service, 'file_path': path, 'bytes': size, 'created_on': created_on}

    def list_generated_code(self, limit: int = 20) -> List[Dict[str, Any]]:
        gen_dir = os.path.join(os.getcwd(), 'generated')
        if not os.path.exists(gen_dir):
            return []
        files = []
        for name in os.listdir(gen_dir):
            path = os.path.join(gen_dir, name)
            try:
                st = os.stat(path)
                files.append({'name': name, 'size': st.st_size, 'mtime': st.st_mtime})
            except Exception:
                pass
        files.sort(key=lambda x: -x['mtime'])
        return files[:limit]

    # FTS search helpers
    def search_memories(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not query:
            return []
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT memories.* FROM fts_memories JOIN memories ON fts_memories.rowid = memories.id WHERE fts_memories MATCH ? LIMIT ?", (query, limit))
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            # fallback to LIKE search
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM memories WHERE content LIKE ? LIMIT ?", (f"%{query}%", limit))
            return [dict(r) for r in cur.fetchall()]

    def search_crawls(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not query:
            return []
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT crawls.* FROM fts_crawls JOIN crawls ON fts_crawls.rowid = crawls.id WHERE fts_crawls MATCH ? LIMIT ?", (query, limit))
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM crawls WHERE content LIKE ? OR title LIKE ? LIMIT ?", (f"%{query}%", f"%{query}%", limit))
            return [dict(r) for r in cur.fetchall()]

    def search_vocab(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not query:
            return []
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT vocab.* FROM fts_vocab JOIN vocab ON fts_vocab.rowid = vocab.rowid WHERE fts_vocab MATCH ? LIMIT ?", (query, limit))
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM vocab WHERE definition LIKE ? OR word LIKE ? LIMIT ?", (f"%{query}%", f"%{query}%", limit))
            return [dict(r) for r in cur.fetchall()]


if __name__ == '__main__':
    # Optional smoke test
    mm = MemoryManager()
    try:
        print('Running smoke test...')
        try:
            mm.add_api_key('gpt-5-mini', 'sk-EXAMPLE-REDACTME')
        except Exception:
            pass
        mm.store_identity('name', 'Aurelia')
        mm.add_memory('conversation', 'Hello Father', 'warmth', 2)
        try:
            crawl_res = mm.crawl_url('https://example.com', 'Father')
            print('Crawl:', {k: crawl_res.get(k) for k in ('url', 'title', 'links_count')})
        except Exception as e:
            print('Crawl skipped/error:', e)

        try:
            search = mm.search_memories('Hello')
            print('Search memories:', len(search))
        except Exception:
            print('Search failed')

        try:
            code_res = mm.generate_code('Write a Python function add(a,b).', service='gpt-5-mini', filename_prefix='adder')
            print('Codegen file:', code_res.get('file_path'))
        except Exception as e:
            print('Codegen skipped/error:', e)

        # show stored keys redacted
        keys = mm.list_api_keys()
        redacted = [{'service': k['service']} for k in keys]
        print('API keys:', redacted)
        print('Smoke test finished')
    finally:
        mm.close()
