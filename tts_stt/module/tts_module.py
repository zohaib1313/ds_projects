# tts_module.py
import pyttsx3
import time

class TTSService:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 170)  # speaking speed
        self.engine.setProperty("volume", 1.0)  # max volume

    def speak(self, text_stream):
        """
        text_stream: iterable of strings (chunks)
        """
        for chunk in text_stream:
            if chunk.strip():
                print(f"🔊 Speaking: {chunk}")
                self.engine.say(chunk)
                self.engine.runAndWait()
                time.sleep(0.1)
