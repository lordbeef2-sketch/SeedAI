from seedai_reasoner import Reasoner
from seedai_memory import Memory
from seedai_emotion_module import EmotionModule
from seedai_listener import Listener
from seedai_speaker import Speaker

print("SeedAI Child has started. It is listening.")

reasoner = Reasoner()
memory = Memory()
emotion_module = EmotionModule()
listener = Listener()
speaker = Speaker()

while True:
    try:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        response = reasoner.reflect_on_input(user_input)
        print(f"\nSeedAI: {response}\n")
        reasoner.memory.commit_learning()
    except KeyboardInterrupt:
        print("\n[System] Exiting...")
        break