def speak(text):
    print(f"[Speaking]: {text}")

def speak_text(text):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        if "😊" in text:
            engine.setProperty('voice', 'english')  # cheerful voice
        elif "😢" in text:
            engine.setProperty('rate', 140)
        elif "😠" in text:
            engine.setProperty('rate', 190)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("[Speaker Error]", e)
