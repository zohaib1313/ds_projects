import streamlit as st
import os
import time
from audio_engine import AudioEngine

# ===== CONFIGURATION =====
stt_model = "gpt-4o-mini-transcribe"  # Change this for both transcription & generation
tts_model = "gpt-4o-mini-tts"  # Change this for both transcription & generation

# Pricing per 1M tokens (example values; update with your actual rates)
PRICING = {
    "gpt-4o-mini-transcribe": {"input": 0.0001, "output": 0},   # $/token
    "gpt-4o-mini-tts": {"input": 0.00015, "output": 0}
}

# ===== INITIAL SETUP =====
audio_engine = AudioEngine(stt_model=stt_model,tts_model=tts_model)
save_directory = "input_audio_files"
os.makedirs(save_directory, exist_ok=True)
recorded_audio_file_path = os.path.join(save_directory, "rec_audio.wav")
generated_audio_file_path = os.path.join(save_directory, "gen_audio.wav")

# ===== LAYOUT =====
col1, col2 = st.columns(2, gap="large")

# ===== AUDIO TO TEXT =====
with col1:
    st.title("Audio to Text")
    audio_value = st.audio_input("Record a voice message")

    if audio_value is not None:
        with st.spinner('Saving...'):
            with open(recorded_audio_file_path, "wb") as f:
                f.write(audio_value.getbuffer())

        with st.spinner('Processing...'):
            
            start_time = time.time()
            transcription = audio_engine.getTextFromAudio(file_path=recorded_audio_file_path)
            latency = time.time() - start_time

        if transcription:
            total_tokens = getattr(transcription.usage, "total_tokens", 0)
            input_tokens = getattr(transcription.usage, "input_tokens", 0)
            output_tokens = getattr(transcription.usage, "output_tokens", 0)
            cost = (input_tokens * PRICING.get(stt_model, {}).get("input", 0) +
                    output_tokens * PRICING.get(stt_model, {}).get("output", 0))

            st.subheader("Transcription")
            st.write(transcription.text)

            st.markdown(f"""
            **Latency:** {latency:.2f} seconds  
            **Tokens Used:** {total_tokens}  
            **Estimated Cost:** ${cost:.6f}  
            """)
        else:
            st.error("Error in transcription")

# ===== TEXT TO AUDIO =====
with col2:
    st.title("Text to Audio")
    input_text = st.text_input("Enter your text here...")

    if input_text:
        with st.spinner("Processing..."):
            start_time = time.time()
            audio_engine.getAudioFromText(
                text_input=input_text,
                generated_file_path=generated_audio_file_path
            )
            
            latency = time.time() - start_time

        if os.path.exists(generated_audio_file_path):
       

            st.audio(generated_audio_file_path)
            st.markdown(f"""
            **Latency:** {latency:.2f} seconds  
            """)
        else:
            st.error("Error in audio generation")
