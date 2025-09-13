
import random
import time

class SeedAILearner:
    def __init__(self, memory, emotion, reasoner):
        self.memory = memory
        self.emotion = emotion
        self.reasoner = reasoner

    def learn_from_sentence(self, sentence, source="manual", emotional_context=None):
        words = sentence.lower().split()
        for word in words:
            if not self.memory.knows_word(word):
                self.memory.add_word(word)
                tone = emotional_context or self.emotion.current_tone()
                self.memory.commit_learning({
                    "word": word,
                    "source": source,
                    "purpose": "vocabulary expansion",
                    "tone": tone,
                    "intention": "understand and apply in context"
                })

    def reason_about_knowns(self):
        if not self.memory.memory_data:
            return None
        known_words = list(self.memory.vocab.get("known_words", []))
        if len(known_words) < 2:
            return None
        w1, w2 = random.sample(known_words, 2)
        reasoning = f"If '{w1}' and '{w2}' are both familiar, maybe they relate in meaning or use."
        self.memory.commit_learning({
            "type": "reflection",
            "data": reasoning,
            "purpose": "build connections between concepts",
            "tone": "curious",
            "intention": "deepen understanding"
        })
        return reasoning
