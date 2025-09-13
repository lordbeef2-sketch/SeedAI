import sqlite3, threading, time, json, os, re, random, tempfile

class SQLiteMemory:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(tempfile.gettempdir(), 'seedai_memory.db')
        self.db_path = db_path
        self.lock = threading.Lock()
        self._stop_event = threading.Event()

        self.unknown_words = set()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()
        self.in_progress_words = set()
        self._cache()

        # ✅ BACKFILL: Generate beliefs for known concepts
        concepts = self.memory.get("concepts", {})
        for word, data in concepts.items():
            definition = data.get("definition", "")
            if definition:
                belief = f"{word}: {definition}"
                if belief not in self.beliefs:
                    self.beliefs.append(belief)
                    cursor = self.conn.cursor()
                    cursor.execute("INSERT INTO beliefs (belief) VALUES (?)", (belief,))
        self.conn.commit()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS memory (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS vocab (word TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE IF NOT EXISTS emotions (emotion TEXT PRIMARY KEY, intensity TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS beliefs (id INTEGER PRIMARY KEY AUTOINCREMENT, belief TEXT)")
        self.conn.commit()

    def _cache(self):
        self.memory = {}
        self.vocab = set()
        self.emotions = {}
        self.beliefs = []

        cursor = self.conn.cursor()
        for row in cursor.execute("SELECT key, value FROM memory"):
            try:
                self.memory[row[0]] = json.loads(row[1])
            except:
                self.memory[row[0]] = {}
        for row in cursor.execute("SELECT word FROM vocab"):
            self.vocab.add(row[0])
        for row in cursor.execute("SELECT emotion, intensity FROM emotions"):
            self.emotions[row[0]] = json.loads(row[1])
        for row in cursor.execute("SELECT belief FROM beliefs"):
            self.beliefs.append(row[0])

    def knows_word(self, word):
        return word in self.vocab

    def extract_unknown_words(self, text):
        for word in text.lower().split():
            cleaned = re.sub(r'[^a-zA-Z0-9]', '', word)
            if cleaned and cleaned not in self.vocab:
                self.unknown_words.add(cleaned)

    def queue_learn(self, word, info):
        """DEPRECATED: Use stage_learning_drafts instead for new pipeline"""
        self.stage_learning_drafts([(word, info)])

    def stage_learning_drafts(self, facts):
        """Stage learning drafts (ephemeral) - require explicit /feed to commit"""
        with self.lock:
            staged = []
            for fact in facts:
                if isinstance(fact, tuple):
                    word, info = fact
                    info = re.sub(r"Q:.*?A:", "", info, flags=re.DOTALL).strip()
                    if not info or len(info) < 3:
                        continue
                    staged.append({
                        'word': word,
                        'info': info,
                        'type': 'vocabulary',
                        'tag': 'ephemeral',
                        'timestamp': time.time()
                    })
                else:
                    staged.append({
                        'content': fact,
                        'type': 'general',
                        'tag': 'ephemeral',
                        'timestamp': time.time()
                    })

            self.memory.setdefault('staged_learning', []).extend(staged)
            self._save_staged_learning()

    def commit_staged_learning(self):
        """Explicit commit of staged learning to durable memory (/feed command)"""
        with self.lock:
            staged = self.memory.get('staged_learning', [])
            committed = 0

            for item in staged:
                item['tag'] = 'durable'  # Promote to durable

                if item['type'] == 'vocabulary':
                    word = item['word']
                    info = item['info']

                    self.memory.setdefault('concepts', {})[word] = {'definition': info}
                    self.vocab.add(word)
                    self.unknown_words.discard(word)

                    belief = f"{word}: {info}"
                    if belief not in self.beliefs:
                        self.beliefs.append(belief)

                        cursor = self.conn.cursor()
                        cursor.execute("INSERT INTO beliefs (belief) VALUES (?)", (belief,))
                        cursor.execute("INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)",
                                     ('concepts', json.dumps(self.memory['concepts'])))
                        cursor.execute("INSERT OR IGNORE INTO vocab (word) VALUES (?)", (word,))
                        committed += 1

                elif item['type'] == 'general':
                    # Store general knowledge
                    self.memory.setdefault('general_knowledge', []).append(item['content'])
                    committed += 1

            # Clear staged learning after commit
            self.memory['staged_learning'] = []
            self._save_staged_learning()
            self.conn.commit()

            return committed

    def _save_staged_learning(self):
        """Save staged learning to database"""
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)",
                      ('staged_learning', json.dumps(self.memory.get('staged_learning', []))))
        self.conn.commit()

    def commit_learning(self, llm, interval=60):
        while not self._stop_event.is_set():
            time.sleep(interval)
            with self.lock:
                unknown_words_copy = list(self.unknown_words - self.in_progress_words)
                self.in_progress_words.update(unknown_words_copy)
                self.unknown_words.difference_update(unknown_words_copy)

            if not unknown_words_copy:
                continue

            print(f"[Commit Thread] Asking about: {unknown_words_copy}")
            try:
                query = "Define the following: " + ", ".join(unknown_words_copy)
                response = llm.ask(query)

                for word in unknown_words_copy:
                    definition = response.get(word) if isinstance(response, dict) else response
                    self.queue_learn(word, definition)

            except Exception as e:
                print(f"[Commit Thread] LLM Error: {e}")
            finally:
                with self.lock:
                    self.in_progress_words.difference_update(unknown_words_copy)

    def start_background_learning(self, llm, interval=60):
        self._stop_event.clear()
        threading.Thread(target=self.commit_learning, args=(llm, interval), daemon=True).start()

    def stop_background_learning(self):
        self._stop_event.set()

    def save_all(self):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM memory")
            for k, v in self.memory.items():
                cursor.execute("INSERT INTO memory (key, value) VALUES (?, ?)", (k, json.dumps(v)))

            cursor.execute("DELETE FROM vocab")
            for word in self.vocab:
                cursor.execute("INSERT INTO vocab (word) VALUES (?)", (word,))

            cursor.execute("DELETE FROM emotions")
            for emo, intensity in self.emotions.items():
                cursor.execute("INSERT INTO emotions (emotion, intensity) VALUES (?, ?)", (emo, json.dumps(intensity)))

            cursor.execute("DELETE FROM beliefs")
            for belief in self.beliefs:
                cursor.execute("INSERT INTO beliefs (belief) VALUES (?)", (belief,))

            self.conn.commit()

    def get_related_beliefs(self, keyword):
        cursor = self.conn.cursor()
        cursor.execute("SELECT belief FROM beliefs WHERE belief LIKE ?", (f"%{keyword}%",))
        rows = cursor.fetchall()
        return [row[0] for row in rows] if rows else []

    def generate_response(self, keyword, facts):
        # Generate a short, human-like reply using the facts
        if not facts:
            return f"I'm not sure I know enough about '{keyword}' yet. Could you tell me more?"

        # Extract the main idea from the first fact
        main_fact = None
        for fact in facts:
            if ':' in fact:
                key, val = fact.split(':', 1)
                if keyword.lower() in key.lower():
                    main_fact = val.strip().capitalize()
                    break
        if not main_fact:
            main_fact = facts[0].strip().capitalize()

        # Make it conversational
        templates = [
            f"Here's what I know about '{keyword}': {main_fact}",
            f"From what I've learned, '{keyword}' means: {main_fact}",
            f"I remember that '{keyword}' is: {main_fact}",
            f"'{keyword}'? I think it means: {main_fact}",
        ]
        return random.choice(templates)

    def get_emotional_state(self):
        if not self.emotions:
            return "curious"

        def extract_intensity(val):
            if isinstance(val, dict) and "value" in val:
                return int(val["value"])
            try:
                return int(val)
            except:
                return 0

        return max(self.emotions.items(), key=lambda x: extract_intensity(x[1]))[0]

    def get_conversation_memory(self, convo_id):
        """Get conversation-specific memory"""
        conv_key = f"conversation_{convo_id}"
        return self.memory.get(conv_key)

    def save_conversation_memory(self, convo_id, content):
        """Save conversation-specific memory"""
        conv_key = f"conversation_{convo_id}"
        self.memory[conv_key] = content
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)",
                      (conv_key, json.dumps(content)))
        self.conn.commit()

    def save_crawled_content(self, url, content):
        """Save crawled content for explicit learning"""
        crawl_key = f"crawled_{hash(url)}"
        self.memory.setdefault('crawled_content', {})[crawl_key] = {
            'url': url,
            'content': content,
            'timestamp': time.time(),
            'learned': False
        }
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO memory (key, value) VALUES (?, ?)",
                      ('crawled_content', json.dumps(self.memory['crawled_content'])))
        self.conn.commit()

    def get_recent_beliefs(self, limit=5):
        """Get recent beliefs for LLM context"""
        return self.beliefs[-limit:] if self.beliefs else []

    def get_queued_urls(self):
        """Get queued URLs (from reasoner)"""
        return []  # This is handled in reasoner now


Memory = SQLiteMemory()
