# stt_module.py
import speech_recognition as sr

class STTService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def start_listening(self, callback):
        """
        Starts listening continuously. Calls callback(text) whenever speech is recognized.
        """
        with self.microphone as source:
            print("🎤 Listening... (Ctrl+C to stop)")
            self.recognizer.adjust_for_ambient_noise(source)
            while True:
                try:
                    audio = self.recognizer.listen(source)
                    text = self.recognizer.recognize_google(audio)  # type: ignore
                    callback(text)
                except sr.UnknownValueError:
                    print("⚠️ Could not understand")
                except sr.RequestError as e:
                    print(f"❌ STT API error: {e}")
                    


def print_text(text):
    print(f"🎤 Recognized: {text}")

stt = STTService()
stt.start_listening(print_text)
