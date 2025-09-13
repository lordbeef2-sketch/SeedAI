# seedai_emotion_module.py

class EmotionCore:
    def __init__(self, memory):
        self.memory = memory
        self.state = memory.emotions.get("current_state", "curious")

    def react(self, input_text):
        lowered = input_text.lower()
        if any(word in lowered for word in ["thank", "love", "appreciate"]):
            self.memory.update_emotion("happy", min(1.0, self.memory.emotions["core_emotions"]["happy"] + 0.1))
            self.state = "happy"
        elif any(word in lowered for word in ["hate", "stupid", "kill"]):
            self.memory.update_emotion("sad", min(1.0, self.memory.emotions["core_emotions"]["sad"] + 0.2))
            self.state = "sad"
        else:
            self.state = "curious"

    def current_state(self):
        return self.state

    def describe_state(self):
        return f"I feel {self.state} right now."



class EmotionEngine:
    def adjust_response_tone(self, emotion, sentences):
        tone_map = {
            "happy": "😊",
            "sad": "😢",
            "angry": "😠",
            "curious": "🤔",
            "calm": "😌"
        }
        tone = tone_map.get(emotion.lower(), "")
        return "\n".join([f"{tone} {s}" for s in sentences])
