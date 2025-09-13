import argparse
from seedai_reasoner import Reasoner
from seedai_feeder import feed_text
from seedai_listener import listen_and_learn
from seedai_speaker import speak, speak_text
from seedai_memory import SQLiteMemory
from seedai_crawler import WebCrawler
from seedai_emotion_module import EmotionCore

# Terminal CLI for SeedAI

def main():
    parser = argparse.ArgumentParser(description="SeedAI Command Line Interface")
    parser.add_argument("command", type=str, help="Command to run (chat, feed, listen, speak, speak_text, crawl, emotion, memory, idle, reload, /feed, /crawl)")
    parser.add_argument("--text", type=str, help="Text input for commands that require it")
    parser.add_argument("--url", type=str, help="URL for crawl command")
    parser.add_argument("--allow-llm", action="store_true", help="Allow LLM usage for this session")
    args = parser.parse_args()

    reasoner = Reasoner()
    memory = reasoner.memory
    allow_llm = args.allow_llm

    if args.command == "chat":
        print("SeedAI CLI chat. Type 'exit' to quit.")
        print(f"LLM permission: {'enabled' if allow_llm else 'disabled'}")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() == "exit":
                break

            # Handle special commands
            if user_input.startswith("/feed"):
                result = reasoner.feed_learning()
                print(f"SeedAI: {result}")
                continue
            elif user_input.startswith("/crawl "):
                url = user_input[7:].strip()
                result = reasoner.crawl_url(url)
                print(f"SeedAI: {result}")
                continue

            # Use new pipeline
            meta = {"allow_llm": allow_llm, "thread_id": "cli_session"}
            response = reasoner.handle_turn(user_input, meta)
            print(f"SeedAI: {response}")
    elif args.command == "feed" and args.text:
        feed_text(args.text)
    elif args.command == "listen" and args.text:
        listen_and_learn(args.text)
    elif args.command == "speak" and args.text:
        speak(args.text)
    elif args.command == "speak_text" and args.text:
        speak_text(args.text)
    elif args.command == "crawl" and args.url:
        crawler = WebCrawler()
        content = crawler.crawl(args.url)
        print(content)
    elif args.command == "emotion" and args.text:
        emotion = EmotionCore(memory)
        emotion.react(args.text)
        print(emotion.describe_state())
    elif args.command == "memory":
        print(memory.memory)
    elif args.command == "idle":
        print("Idle thinking not implemented in CLI yet.")
    elif args.command == "reload":
        print("Reload not implemented in CLI yet.")
    else:
        print("Unknown or incomplete command. See --help.")

if __name__ == "__main__":
    main()
