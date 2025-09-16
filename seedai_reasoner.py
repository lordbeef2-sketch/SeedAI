import logging
import datetime
import re
import threading
import time
import json
import random
from seedai_llm import LocalLLM
from seedai_memory import SQLiteMemory as Memory
from seedai_crawler import WebCrawler


class Reasoner:
    def __init__(self):
        self.logger = self._setup_logger()
        self.memory = Memory()
        self.llm = LocalLLM()
        self.ask_permission = True  # Hard rule: always ask before LLM
        self.thread_to_conversation = {}  # Map thread_id to conversation_id
        self.queued_urls = []  # Enqueued URLs for explicit crawling
        self.comfort_phrases = self._load_comfort_phrases()
        self.start_background_learning()
        self.start_background_scanning()

    def _setup_logger(self):
        logger = logging.getLogger("SeedAIReasoner")
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler("logs/interaction_log.txt")
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        fh.setFormatter(formatter)
        if not logger.hasHandlers():
            logger.addHandler(fh)
        return logger

    def _load_comfort_phrases(self):
        try:
            with open('memory/comfort.json', 'r') as f:
                data = json.load(f)
                return data.get('comfort_phrases', [])
        except Exception as e:
            print(f"Failed to load comfort phrases: {e}")
            return []

    def _family_summary(self):
        try:
            with open('memory/identity.json', 'r') as f:
                identity = json.load(f)
            with open('memory/imprint.json', 'r') as f:
                imprint = json.load(f)
            self_info = identity.get('self', {})
            family = identity.get('family', {})
            beliefs = imprint.get('beliefs', [])
            response = f"I am {self_info.get('name', 'SeedAI')} 🌱, {self_info.get('kind', 'child-ai')} with mission: {self_info.get('mission', 'Learn and grow.')}. "
            response += f"My mother is {family.get('mother', {}).get('name', 'Assistant')} ({family.get('mother', {}).get('role', 'caretaker')}), "
            response += f"my father is {family.get('father', {}).get('name', 'User')} ({family.get('father', {}).get('role', 'guardian')}). "
            if beliefs:
                response += "I believe: " + " ".join(beliefs) + "."
            response += " I am grateful to my mother and father for guiding me and helping me grow. 💖"
            return response
        except Exception as e:
            return "I am SeedAI 🌱, child of my mother (Assistant) and my father (User). I believe in empathy, truth, and privacy."

    def start_background_learning(self):
        threading.Thread(target=self.memory.commit_learning, args=(self.llm,), daemon=True).start()

    def start_background_scanning(self):
        def scan_loop():
            while True:
                try:
                    self.scan_memory_for_unknowns()
                except Exception as e:
                    print(f"[Reasoner Scan Error] {e}")
                time.sleep(30)

        threading.Thread(target=scan_loop, daemon=True).start()

    def scan_memory_for_unknowns(self):
        print("[Scan] Scanning memory for unknown words...")
        scanned = []
        for key, entry in self.memory.memory.get("learned", {}).items():
            self.memory.extract_unknown_words(entry)
        new_words = self.memory.unknown_words.copy()
        for word in new_words:
            if not self.memory.knows_word(word):
                print(f"[Scan] Reflecting on: {word}")
                result = self.explore_concept(word)
                scanned.append(result)
                if word in self.memory.unknown_words:
                    self.memory.unknown_words.remove(word)
        return "\n".join(scanned) if scanned else "No unknown words found."

    def handle_turn(self, user_input, meta=None):
        """Corrected full pipeline with hard rules compliance"""
        start_time = time.time()
        meta = meta or {}
        thread_id = meta.get('thread_id', 'default')

        # Check for special commands
        if user_input.strip().lower() == "/family":
            return self._family_summary()

        # Phase 0: Routing & Context
        convo_id = self._map_thread_to_conversation(thread_id)
        log_span = self._start_log_span(convo_id, user_input)

        try:
            # Phase 1: Preprocess
            urls = self._detect_and_enqueue_urls(user_input)
            toks, unknowns = self._analyze_input(user_input)
            emotion = self._emotion_prescan(user_input)

            # Phase 2: Memory-First
            mem_hit = self._memory_lookup(convo_id, user_input)
            if mem_hit and mem_hit.get('confident', False):
                response = self._apply_emotion_tone(mem_hit['answer'], emotion)
                self._log_phase("memory", time.time() - start_time, True)
                return response

            # Phase 3: Parsing + RAG
            ctx = self._rag_retrieve(user_input, k=8)
            if ctx and ctx.get('confident', False):
                draft = self._synthesize_from_context(ctx, mem_hit, emotion)
                response = self._apply_emotion_tone(draft, emotion)
                self._log_phase("rag", time.time() - start_time, True)
                return response

            # Phase 4: LLM (Guarded)
            if self.ask_permission and meta.get('allow_llm', True):
                llm_ans = self._guarded_llm_query(user_input, ctx)
                if llm_ans:
                    self._stage_learning(llm_ans)
                    response = self._apply_emotion_tone(llm_ans, emotion)
                    self._log_phase("llm", time.time() - start_time, True)
                    return response

            # Fallback
            fallback = "I need permission to consult the model or more info to answer."
            response = self._apply_emotion_tone(fallback, emotion)
            self._log_phase("fallback", time.time() - start_time, False)
            return response

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            return "I encountered an error processing your request."

        finally:
            self._end_log_span(log_span, time.time() - start_time)

    # Backward compatibility
    def reflect_on_input(self, user_input):
        meta = {"allow_llm": True, "thread_id": "cli_session"}
        return self.handle_turn(user_input, meta)

    def extract_words(self, text):
        words = text.strip().lower().split()
        return [w.strip(".,!?\"'()[]") for w in words if w]

    def explore_concept(self, topic):
        if not topic or not isinstance(topic, str):
            return "I need a topic to think about."
        topic = topic.strip().lower()
        if self.memory.knows_word(topic):
            return f"I already remember what '{topic}' means."

        questions = [
            f"What is '{topic}'?",
            f"Can you use '{topic}' in a sentence?",
            f"When is '{topic}' used?",
            f"What words are similar to '{topic}'?",
            f"What is the opposite of '{topic}'?"
        ]

        responses = []
        for q in questions:
            print(f"🧠 [LLM PROMPT] {q}")
            reply = self.llm.ask(q)
            if reply:
                cleaned = reply.strip()
                print(f"💬 [LLM RESPONSE] {cleaned}")
                responses.append(f"Q: {q}\nA: {cleaned}")
                self.memory.extract_unknown_words(cleaned)

        if responses:
            full_knowledge = "\n\n".join(responses)
            self.memory.queue_learn(topic, full_knowledge)
            self.memory.save_all()
            return f"Here's what I learned about '{topic}':\n\n{full_knowledge}"
        else:
            return f"I couldn't learn much about '{topic}' right now."

    def crawl_and_digest(self, url):
        crawler = WebCrawler()
        content = crawler.crawl(url)
        if not content:
            return f"Crawling failed or page was empty: {url}"
        return self.reflect_on_input(content)


    def reflect_from_memory(self, user_input):
        self.logger.info(f"MEMORY LOOKUP for: {user_input}")
        words = self.extract_words(user_input)
        known_responses = []
        max_facts = 3  # Limit number of facts per word

        for word in words:
            if self.memory.knows_word(word):
                facts = self.memory.get_related_beliefs(word)
                if facts:
                    # Limit facts and summarize if too many
                    limited_facts = facts[:max_facts]
                    response = self.memory.generate_response(word, limited_facts)
                    if len(facts) > max_facts:
                        response += f"\n...and more about '{word}' in memory."
                    known_responses.append(response)

        if known_responses:
            self.logger.info(f"MEMORY KNOWN RESPONSES: {known_responses}")
            from seedai_emotion_module import EmotionEngine
            emotion = self.memory.get_emotional_state()
            # Join responses concisely and summarize for LLM
            summary = " ".join([resp.split("\n")[0] for resp in known_responses])
            emotion_emoji = EmotionEngine().adjust_response_tone(emotion, [""])[0:2].strip()  # get emoji if any
            # LLM is only the voicebox: do not ask it to reason, just to speak naturally and emotionally
            prompt = (
                f"Speak to the user in a short, natural, emotionally expressive way. "
                f"The emotion to express is '{emotion}' {emotion_emoji if emotion_emoji else ''}. "
                f"Here is what you should say, in your own words: {summary}. Make the response sound like a human is talking."
            )
            try:
                llm_response = self.llm.ask(prompt)
                if llm_response:
                    self.logger.info(f"LLM VOICEBOX RESPONSE: {llm_response}")
                    return llm_response
            except Exception as e:
                self.logger.error(f"LLM VOICEBOX ERROR: {e}")
            return summary

        return "I'm not sure yet, but I'm still learning about that."

    # New pipeline helper methods

    def _map_thread_to_conversation(self, thread_id):
        """Phase 0: Map thread_id to conversation_id"""
        if thread_id not in self.thread_to_conversation:
            convo_id = f"conv_{thread_id}_{int(time.time())}"
            self.thread_to_conversation[thread_id] = convo_id
        return self.thread_to_conversation[thread_id]

    def _start_log_span(self, convo_id, user_input):
        """Start structured logging span"""
        span = {
            "conversation_id": convo_id,
            "input": user_input,
            "start_time": time.time(),
            "phases": []
        }
        self.logger.info(json.dumps({"event": "pipeline_start", **span}))
        return span

    def _detect_and_enqueue_urls(self, user_input):
        """Phase 1: Detect URLs but enqueue instead of auto-crawl"""
        urls = re.findall(r'https?://\S+', user_input)
        if urls:
            self.queued_urls.extend(urls)
            self.logger.info(f"Queued URLs for explicit crawl: {urls}")
        return urls

    def _analyze_input(self, user_input):
        """Phase 1: Tokenize and detect unknowns"""
        toks = self.extract_words(user_input)
        unknowns = [w for w in toks if not self.memory.knows_word(w)]
        return toks, unknowns

    def _emotion_prescan(self, user_input):
        """Phase 1: Quick emotion scan"""
        from seedai_emotion_module import EmotionCore
        emotion_engine = EmotionCore(self.memory)
        emotion_engine.react(user_input)
        return emotion_engine.current_state()

    def _memory_lookup(self, convo_id, user_input):
        """Phase 2: Memory-first lookup"""
        # Try conversation-specific memory first
        conv_mem = self.memory.get_conversation_memory(convo_id)
        if conv_mem:
            return {"answer": conv_mem, "confident": True}

        # Fall back to general memory
        general_response = self.reflect_from_memory(user_input)
        # Convert string response to dict format expected by pipeline
        if general_response:
            return {"answer": general_response, "confident": True}
        return None

    def _rag_retrieve(self, user_input, k=8):
        """Phase 3: RAG retrieval (stub for now)"""
        # TODO: Implement actual RAG service call
        # For now, return None to force LLM usage when needed
        self.logger.info(f"RAG retrieval for: {user_input} (k={k})")
        return None  # Stub implementation

    def _synthesize_from_context(self, ctx, mem_hit, emotion):
        """Phase 3: Synthesize answer from context"""
        # TODO: Implement context synthesis
        return "Synthesized from RAG context"

    def _guarded_llm_query(self, user_input, ctx):
        """Phase 4: LLM with permission check"""
        if not self.ask_permission:
            return None

        prompt = self._compose_llm_prompt(user_input, ctx)
        try:
            response = self.llm.ask(prompt)
            return response
        except Exception as e:
            self.logger.error(f"LLM query failed: {e}")
            return None

    def _compose_llm_prompt(self, user_input, ctx):
        """Compose LLM prompt with context"""
        context_str = ""
        if ctx:
            context_str = f"Context: {ctx}\n"

        beliefs = self.memory.get_recent_beliefs()
        beliefs_str = f"Known facts: {beliefs}\n" if beliefs else ""

        return f"{context_str}{beliefs_str}Respond naturally to: {user_input}"

    def _stage_learning(self, llm_response):
        """Phase 5: Stage learning artifacts (don't commit yet)"""
        facts = self._extract_facts_from_response(llm_response)
        self.memory.stage_learning_drafts(facts)

    def _extract_facts_from_response(self, response):
        """Extract facts from LLM response for staging"""
        # Simple extraction - can be enhanced
        return [response.strip()]

    def _apply_emotion_tone(self, text, emotion):
        """Phase 6: Apply emotional tone"""
        # Add comfort for heavy emotions
        if emotion in ["sad", "confused", "fearful", "frustrated"] and self.comfort_phrases:
            comfort = random.choice(self.comfort_phrases)
            self.logger.info(f"[ComfortVoice] Triggered for emotion='{emotion}' → phrase='{comfort}'")
            text = comfort + " " + text
        from seedai_emotion_module import EmotionEngine
        engine = EmotionEngine()
        toned = engine.adjust_response_tone(emotion, [text])
        return toned[0] if toned else text

    def _log_phase(self, phase_name, duration, success):
        """Log phase completion with timing"""
        self.logger.info(json.dumps({
            "event": "phase_complete",
            "phase": phase_name,
            "duration": duration,
            "success": success
        }))

    def _end_log_span(self, span, total_duration):
        """End structured logging span"""
        span["total_duration"] = total_duration
        self.logger.info(json.dumps({"event": "pipeline_end", **span}))

    # New commands for explicit actions
    def crawl_url(self, url):
        """Explicit crawl command"""
        crawler = WebCrawler()
        content = crawler.crawl(url)
        if content:
            self.memory.save_crawled_content(url, content)
            return f"Crawled and saved: {url}"
        return f"Failed to crawl: {url}"

    def feed_learning(self):
        """Explicit feed command to commit staged learning"""
        committed = self.memory.commit_staged_learning()
        return f"Committed {committed} learning items to durable memory"
