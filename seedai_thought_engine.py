
import threading
import time

class SeedAIThoughtEngine:
    def __init__(self, learner, memory, interval=60):
        self.learner = learner
        self.memory = memory
        self.interval = interval
        self.running = False
        self.thread = None

    def start_thinking(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._thought_loop, daemon=True)
            self.thread.start()

    def stop_thinking(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _thought_loop(self):
        while self.running:
            reflection = self.learner.reason_about_knowns()
            if reflection:
                print(f"[Idle Thought] {reflection}")
            time.sleep(self.interval)
