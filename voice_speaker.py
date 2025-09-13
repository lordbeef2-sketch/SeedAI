
import pyttsx3

class SeedAISpeaker:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)

    def say(self, text):
        print(f"[SeedAI says] {text}")
        self.engine.say(text)
        self.engine.runAndWait()
