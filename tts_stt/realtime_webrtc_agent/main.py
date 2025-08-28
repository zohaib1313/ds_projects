import os
import textwrap
import json
from flask import Flask, jsonify, Response, request
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REALTIME_MODEL = "gpt-4o-realtime-preview-2025-06-03"
ASSISTANT_MODEL = "gpt-4o-mini"  # For your custom agent
TTS_MODEL = "tts-1"  # Text-to-speech model
TTS_VOICE = "alloy"  # Voice for TTS
IS_MP3 = False

if not OPENAI_API_KEY:
    raise SystemExit("Please set OPENAI_API_KEY environment variable.")

app = Flask(__name__)


def call_custom_agent(text):
    """
    Replace this function with your custom agent logic.
    This should return a generator that yields text chunks for streaming.
    """
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": ASSISTANT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. Respond briefly and conversationally.",
                    },
                    {"role": "user", "content": text},
                ],
                "stream": True,
                "max_tokens": 200,
            },
            stream=True,
            timeout=30,
        )

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        yield f"Error calling agent: {str(e)}"


def text_to_speech_stream(text):
    """Convert text to speech and return audio data"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": TTS_MODEL,
                "input": text,
                "voice": TTS_VOICE,
                "response_format": "mp3",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"TTS Error: {e}")
        return None


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@app.route("/")
def index():
    """Serves a single-page HTML client"""
    html = f"""\
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>Live Transcription + Custom Agent</title>
      <style>
        body {{ font-family: system-ui, sans-serif; margin: 40px; background: #f8fafc; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        button {{ 
          padding: 12px 24px; margin-right: 12px; border: none; border-radius: 8px;
          cursor: pointer; font-size: 14px; font-weight: 500;
        }}
        #startBtn {{ background: #16a34a; color: white; }}
        #startBtn:hover {{ background: #15803d; }}
        #startBtn:disabled {{ background: #9ca3af; cursor: not-allowed; }}
        #stopBtn {{ background: #dc2626; color: white; }}
        #stopBtn:hover {{ background: #b91c1c; }}
        #stopBtn:disabled {{ background: #9ca3af; cursor: not-allowed; }}
        .transcription-box {{ 
          background: white; border: 2px solid #e5e7eb; border-radius: 12px;
          padding: 20px; margin: 20px 0; min-height: 100px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .live-transcription {{
          font-size: 18px; line-height: 1.6; color: #1f2937;
          min-height: 60px;
        }}
        .typing {{ color: #6b7280; }}
        .final {{ color: #1f2937; font-weight: 500; }}
        .agent-response {{ 
          background: #f0f9ff; border: 2px solid #0ea5e9; 
          border-radius: 12px; padding: 20px; margin: 20px 0;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .status {{ 
          padding: 8px 16px; background: #fef3c7; border-radius: 6px;
          color: #92400e; font-size: 14px; margin: 10px 0;
        }}
        .tag {{ 
          display: inline-block; background: #f1f5f9; border: 1px solid #cbd5e1;
          padding: 4px 12px; border-radius: 20px; font-size: 12px; margin-right: 8px;
        }}
        .controls {{ text-align: center; margin: 20px 0; }}
        h1 {{ text-align: center; color: #1f2937; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #6b7280; margin-bottom: 30px; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🎤 Live Transcription + Custom Agent</h1>
        <p class="subtitle">Speak to see real-time transcription, then get AI responses</p>
        
        <div class="controls">
          <button id="startBtn">🎤 Start Recording</button>
          <button id="stopBtn" disabled>⏹️ Stop & Send to Agent</button>
        </div>
        
        <div>
          <span class="tag">transcription: {REALTIME_MODEL}</span>
          <span class="tag">agent: {ASSISTANT_MODEL}</span>
          <span class="tag">voice: {TTS_VOICE}</span>
        </div>

        <div class="transcription-box">
          <div class="live-transcription" id="transcription">
            <span class="typing">Start recording to see live transcription...</span>
          </div>
        </div>

        <div id="agentResponse" class="agent-response" style="display: none;">
          <h3>🤖 Agent Response:</h3>
          <div id="agentText"></div>
        </div>

        <div id="status"></div>
      </div>

      <script>
        const startBtn = document.getElementById("startBtn");
        const stopBtn = document.getElementById("stopBtn");
        const transcriptionEl = document.getElementById("transcription");
        const agentResponseEl = document.getElementById("agentResponse");
        const agentTextEl = document.getElementById("agentText");
        const statusEl = document.getElementById("status");

        let pc = null;
        let dc = null;
        let localStream = null;
        let currentTranscription = "";
        let currentAudio = null;

        function showStatus(message, type = "info") {{
          statusEl.innerHTML = `<div class="status">${{message}}</div>`;
          if (type === "clear") {{
            setTimeout(() => statusEl.innerHTML = "", 3000);
          }}
        }}

      function updateTranscription(text, isFinal = false) {{
  const transcriptionEl = document.getElementById("transcription");

  if (isFinal) {{
    // Append final text to the transcription and update the saved text
    currentTranscription += " " + text;
    transcriptionEl.innerHTML = `<span class="final">${{currentTranscription}}</span>`;
  }} else {{
    // Show temporary typing text along with the accumulated transcription
    transcriptionEl.innerHTML = `<span class="final">${{currentTranscription}}</span> <span class="typing">${{text}}</span>`;
  }}
}}

        async function createSessionEphemeralKey() {{
          const r = await fetch("/session");
          if (!r.ok) {{
            throw new Error("Failed to mint ephemeral token: " + await r.text());
          }}
          const data = await r.json();
          return data.client_secret.value;
        }}

        async function sendToAgent(text) {{
          if (!text.trim()) {{
            showStatus("❌ No transcription to send to agent");
            return;
          }}

          try {{
            agentResponseEl.style.display = "block";
            agentTextEl.textContent = "";
            showStatus("🤖 Sending to custom agent...");
            
            const response = await fetch("/agent", {{
              method: "POST",
              headers: {{
                "Content-Type": "application/json"
              }},
              body: JSON.stringify({{ text: text }})
            }});

            if (!response.ok) {{
              throw new Error("Agent request failed");
            }}

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let agentResponse = "";

            showStatus("🤖 Receiving response...");

            while (true) {{
              const {{ done, value }} = await reader.read();
              if (done) break;

              const chunk = decoder.decode(value);
              const lines = chunk.split('\\n');
              
              for (const line of lines) {{
                if (line.startsWith('data: ')) {{
                  const data = line.substring(6);
                  if (data === '[DONE]') {{
                    break;
                  }}
                  try {{
                    const json = JSON.parse(data);
                    if (json.content) {{
                      agentResponse += json.content;
                      agentTextEl.textContent = agentResponse;
                    }}
                  }} catch (e) {{
                    // Ignore JSON parse errors for partial chunks
                  }}
                }}
              }}
            }}

            if (agentResponse) {{
              showStatus("🔊 Converting to speech...");
              
              // Convert to speech
              const audioResponse = await fetch("/tts", {{
                method: "POST",
                headers: {{
                  "Content-Type": "application/json"
                }},
                body: JSON.stringify({{ text: agentResponse }})
              }});

              if (audioResponse.ok) {{
                const audioBlob = await audioResponse.blob();
                const audioUrl = URL.createObjectURL(audioBlob);
                
                // Stop any currently playing audio
                if (currentAudio) {{
                  currentAudio.pause();
                  currentAudio.currentTime = 0;
                }}
                
                currentAudio = new Audio(audioUrl);
                currentAudio.onended = () => {{
                  showStatus("✅ Response complete. You can start recording again.", "clear");
                }};
                currentAudio.play();
                showStatus("🔊 Playing response...");
              }} else {{
                if (audioResponse.status === 300) {{
                 
                }} else {{
                  showStatus("❌ Text-to-speech failed");
                }}
              }}
            }}

          }} catch (error) {{
            showStatus("❌ Agent error: " + error.message);
          }}
        }}

        async function connect() {{
          const EPHEMERAL_KEY = await createSessionEphemeralKey();

          pc = new RTCPeerConnection();
          dc = pc.createDataChannel("oai-events");

          let partialTranscript = "";

          dc.onmessage = (e) => {{
            try {{
              const msg = JSON.parse(e.data);

              // Real-time partial transcription
              if (msg.type === "conversation.item.input_audio_transcription.delta" && msg.delta) {{
                partialTranscript += msg.delta;
                updateTranscription(partialTranscript, false);
              }}

              // Final transcription when user stops speaking
              if (msg.type === "conversation.item.input_audio_transcription.completed" && msg.transcript) {{
                updateTranscription(msg.transcript, true);
                partialTranscript = ""; // Reset for next utterance
              }}

            }} catch (_) {{
              // Ignore non-JSON messages
            }}
          }};

          dc.onopen = () => {{
            const sessionConfig = {{
              type: "session.update",
              session: {{
                input_audio_transcription: {{
                  model: "whisper-1"
                }},
                turn_detection: {{
                  type: "server_vad",
                  threshold: 0.5,
                  prefix_padding_ms: 300,
                  silence_duration_ms: 500
                }},
                modalities: ["text"], // Only text, no audio output
                instructions: "Only transcribe. Do not respond."
              }}
            }};
            dc.send(JSON.stringify(sessionConfig));
            showStatus("🎤 Recording started. Speak now...", "clear");
          }};

          // Add microphone
          localStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
          localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

          // Create offer
          const offer = await pc.createOffer({{ offerToReceiveAudio: true }});
          await pc.setLocalDescription(offer);

          // Send to OpenAI Realtime API
          const baseUrl = "https://api.openai.com/v1/realtime";
          const sdpResponse = await fetch(`${{baseUrl}}?model={REALTIME_MODEL}`, {{
            method: "POST",
            body: offer.sdp,
            headers: {{
              Authorization: `Bearer ${{EPHEMERAL_KEY}}`,
              "Content-Type": "application/sdp",
              "OpenAI-Beta": "realtime=v1"
            }},
          }});
          const answerSDP = await sdpResponse.text();
          await pc.setRemoteDescription({{ type: "answer", sdp: answerSDP }});
        }}

        startBtn.onclick = async () => {{
          startBtn.disabled = true;
          agentResponseEl.style.display = "none";
          updateTranscription("Connecting...", false);
          
          try {{
            await connect();
            stopBtn.disabled = false;
          }} catch (err) {{
            showStatus("❌ Error: " + err.message);
            startBtn.disabled = false;
            updateTranscription("Click 'Start Recording' to begin...", false);
          }}
        }};

        stopBtn.onclick = async () => {{
          stopBtn.disabled = true;
          
          // Stop current audio if playing
          if (currentAudio) {{
            currentAudio.pause();
            currentAudio.currentTime = 0;
          }}
          
          // Close connections
          if (dc) dc.close();
          if (pc) pc.close();
          if (localStream) localStream.getTracks().forEach(t => t.stop());
          
          showStatus("🛑 Recording stopped. Processing...");
          
          // Send transcription to agent
          await sendToAgent(currentTranscription);
          
          startBtn.disabled = false;
        }};
      </script>
    </body>
    </html>
    """
    return Response(textwrap.dedent(html), mimetype="text/html")


@app.route("/session", methods=["GET"])
def create_session():
    """Mint an ephemeral OpenAI Realtime key for transcription only."""
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    payload = {
        "model": REALTIME_MODEL,
        "modalities": ["text"],  # Only text, no audio output
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return jsonify(r.json())


@app.route("/agent", methods=["POST"])
def agent_endpoint():
    """Process text with custom agent and return streaming response."""
    data = request.json
    text = data.get("text", "") if data else ""

    if not text:
        return jsonify({"error": "No text provided"}), 400

    def generate():
        yield "data: " + json.dumps({"status": "starting"}) + "\n\n"

        for chunk in call_custom_agent(text):
            if chunk:
                yield "data: " + json.dumps({"content": chunk}) + "\n\n"

        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/plain")


# tts_module.py
import pyttsx3


class TTSService:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 200)  # speaking speed
        self.engine.setProperty("volume", 1.0)  # max volume

    def speakAll(self, text):
        self.engine.say(text)
        self.engine.runAndWait()


tts = TTSService()


@app.route("/tts", methods=["POST"])
def text_to_speech():
    """Convert text to speech."""
    data = request.json
    text = data.get("text", "") if data else ""
    if not IS_MP3:
        tts.speakAll(text)
        return jsonify({"tts_service": ""}), 300
    else:
        if not text:
            return jsonify({"error": "No text provided"}), 400

        audio_data = text_to_speech_stream(text)
        if audio_data:
            return Response(audio_data, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "TTS failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
