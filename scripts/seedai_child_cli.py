# DEV TOOL: Do not remove. This CLI loop is used for quick local testing when the web UI is down.

from seedai_reasoner import Reasoner

if __name__ == "__main__":
    print("SeedAI Child has started. It is listening.")
    reasoner = Reasoner()
    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            response = reasoner.reflect_on_input(user_input)
            print(f"\nSeedAI: {response}\n")
            # make sure this calls your staged commit only if allowed
            try:
                reasoner.memory.commit_learning()
            except Exception:
                pass
    except KeyboardInterrupt:
        print("\n[System] Exiting...")