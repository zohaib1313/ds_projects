import os
from dotenv import load_dotenv
from openai import OpenAI
import openai

load_dotenv()

class AudioEngine:
    def __init__(self, stt_model="gpt-4o-transcribe", tts_model="gpt-4o-mini-tts", voice="alloy"):
        self.openAiKey = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openAiKey)
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.voice = voice

    def getTextFromAudio(self, file_path):
        try:
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.stt_model,
                    file=audio_file
                )
            print(f"[STT] Transcription: {transcript.text}")
            return transcript
        except Exception as e:
            print(f"[STT] Exception: {e}")
            return None

    def getAudioFromText(self, text_input, generated_file_path):
        try:
            with openai.audio.speech.with_streaming_response.create(
                model=self.tts_model,
                voice=self.voice,
                input=text_input,
            ) as response:
                response.stream_to_file(generated_file_path)
                print(f"[TTS] File saved: {generated_file_path}")
        except Exception as e:
            print(f"[TTS] Exception: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    engine = AudioEngine(
        stt_model="gpt-4o-transcribe",
        tts_model="gpt-4o-mini-tts",
        voice="alloy"
    )

    # Speech-to-Text
    transcript = engine.getTextFromAudio("sample.wav")
    
    # Text-to-Speech
    if transcript and transcript.text:
        engine.getAudioFromText(transcript.text, "output.mp3")
