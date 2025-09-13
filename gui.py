import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from seedai_reasoner import Reasoner
import threading
import importlib

import seedai_learning

from voice_speaker import SeedAISpeaker
from seedai_learning import SeedAILearner
from seedai_thought_engine import SeedAIThoughtEngine

class SeedAIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SeedAI GUI")
        self.root.geometry("750x600")

        self.reasoner = Reasoner()
        self.allow_llm = True  # Default to allow LLM in GUI
        self.speaker = SeedAISpeaker()
        self.learner = None
        self.thought_engine = None
        self.is_muted = False

        self.chat_display = tk.Text(root, height=25, width=85)
        self.chat_display.pack(pady=10)

        self.entry = tk.Entry(root, width=60)
        self.entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))

        self.send_button = tk.Button(root, text="Send", command=self.process_input)
        self.send_button.pack(side=tk.LEFT, padx=(5, 10), pady=(0, 10))

        self.create_command_buttons()

        self.display_message("System", "SeedAI GUI started. You can chat now.")
        self.start_background_ai_interaction()

    def create_command_buttons(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=5)

        tk.Button(frame, text="🧠 Think", command=lambda: self.send_command("#think")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="📚 Learn", command=self.learn_input_popup).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="🔄 Idle Thoughts ON", command=lambda: self.send_command("#idle on")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="🛑 Idle OFF", command=lambda: self.send_command("#idle off")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="🔈 Say Out Loud", command=self.say_input_popup).pack(side=tk.LEFT, padx=5)

        self.mute_btn = tk.Button(frame, text="🔇 Mute", command=self.toggle_mute)
        self.mute_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(frame, text="🔁 Reload", command=lambda: self.send_command("#reload")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="🤖 Toggle LLM", command=lambda: self.send_command("#toggle-llm")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="📥 Feed Learn", command=lambda: self.send_command("/feed")).pack(side=tk.LEFT, padx=5)

    def process_input(self):
        text = self.entry.get()
        self.entry.delete(0, tk.END)
        if not text.strip():
            return
        self.display_message("You", text)
        threading.Thread(target=self.process_user_input, args=(text,), daemon=True).start()

    def process_user_input(self, text):
        if text.startswith("#") or text.startswith("/"):
            response = self.handle_command(text)
        else:
            # Use new corrected pipeline
            meta = {"allow_llm": self.allow_llm, "thread_id": "gui_session"}
            response = self.reasoner.handle_turn(text, meta)

        # Only speak if not muted and not a command
        if not self.is_muted and not text.startswith("#") and not text.startswith("/"):
            self.speaker.say(response)

    def display_message(self, sender, message):
        self.chat_display.insert(tk.END, f"{sender}: {message}\n")
        self.chat_display.see(tk.END)

    def send_command(self, command):
        response = self.handle_command(command)
        self.display_message("Command", f"{command}\n{response}")

    def learn_input_popup(self):
        text = simpledialog.askstring("Learn", "Enter a sentence to learn:")
        if text:
            self.send_command(f"#learn {text}")

    def say_input_popup(self):
        text = simpledialog.askstring("Say Out Loud", "What should SeedAI say?")
        if text:
            self.send_command(f"#say {text}")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        new_text = "🔇 Mute" if not self.is_muted else "🔊 Unmute"
        self.mute_btn.config(text=new_text)
        self.display_message("System", f"Voice {'muted' if self.is_muted else 'unmuted'}.")

    def handle_command(self, command):
        if self.learner is None:
            self.learner = SeedAILearner(self.reasoner.memory, self.reasoner.emotion, self.reasoner)

        if command.startswith("#mute"):
            self.is_muted = True
            return "Voice output muted."
        elif command.startswith("#unmute"):
            self.is_muted = False
            return "Voice output unmuted."
        elif command.startswith("#say "):
            text = command[5:]
            if not self.is_muted:
                self.speaker.say(text)
            return f"Said: {text}"
        elif command.startswith("#learn "):
            sentence = command[7:]
            self.learner.learn_from_sentence(sentence)
            return f"Learned from: {sentence}"
        elif command.startswith("#think"):
            reasoning = self.learner.reason_about_knowns()
            if reasoning and not self.is_muted:
                self.speaker.say(reasoning)
            return reasoning or "Nothing to reflect on yet."
        elif command.startswith("#reload"):
            importlib.reload(seedai_learning)
            self.learner = SeedAILearner(self.reasoner.memory, self.reasoner.emotion, self.reasoner)
            return "Learning module reloaded."
        elif command.startswith("#idle on"):
            if not self.thought_engine:
                self.thought_engine = SeedAIThoughtEngine(self.learner, self.reasoner.memory)
                self.thought_engine.start_thinking()
                return "Idle thinking started."
            return "Idle thinking already running."
        elif command.startswith("#idle off"):
            if self.thought_engine:
                self.thought_engine.stop_thinking()
                self.thought_engine = None
                return "Idle thinking stopped."
            return "Idle thinking not active."
        elif command.startswith("/feed"):
            result = self.reasoner.feed_learning()
            return result
        elif command.startswith("/crawl "):
            url = command[7:].strip()
            result = self.reasoner.crawl_url(url)
            return result
        elif command.startswith("#toggle-llm"):
            self.allow_llm = not self.allow_llm
            return f"LLM permission {'enabled' if self.allow_llm else 'disabled'}."
        return "Unknown command."

    def start_background_ai_interaction(self):
        def run():
            while True:
                try:
                    print("[Scan] Scanning memory for unknown words...")
                    self.reasoner.scan_memory_for_unknowns()
                    vocab = list(self.reasoner.memory.vocab)
                    for word in vocab:
                        self.reasoner.explore_concept(word)
                except Exception as e:
                    print(f"[Reasoner Scan Error] {e}")
                import time
                time.sleep(60)

        threading.Thread(target=run, daemon=True, name="background_ai_interaction").start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SeedAIGUI(root)
    root.mainloop()
