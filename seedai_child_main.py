from seedai_reasoner import Reasoner

print("SeedAI Child has started. It is listening.")
reasoner = Reasoner()

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