from seedai_reasoner import Reasoner

reasoner = Reasoner()

def listen_and_learn(heard_text):
    print(f"[Heard]: {heard_text}")
    result = reasoner.reflect_on_input(heard_text)
    print(f"[Learned]:\n{result}")
    reasoner.memory.commit_learning()