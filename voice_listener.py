
import queue
import sounddevice as sd
import vosk
import sys
import json

class SeedAIListener:
    def __init__(self, model_path="model"):
        self.model = vosk.Model(model_path)
        self.q = queue.Queue()
        self.device = None
        self.samplerate = 16000

    def listen_once(self):
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, dtype="int16",
                               channels=1, callback=self._callback):
            rec = vosk.KaldiRecognizer(self.model, self.samplerate)
            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    return result.get("text", "")

    def _callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))
