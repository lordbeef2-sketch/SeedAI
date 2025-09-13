from seedai_reasoner import Reasoner

reasoner = Reasoner()

def feed_text(text):
    print(f"[Feed]: {text}")
    result = reasoner.reflect_on_input(text)
    print(f"[Result]:\n{result}")
    reasoner.memory.commit_learning()

def tell_memory():
    print("[Speak from Memory]")
    print(reasoner.memory.form_sentence())
