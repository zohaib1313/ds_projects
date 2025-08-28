import os
import textwrap
from flask import Flask, jsonify, Response
import requests
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REALTIME_MODEL = "gpt-4o-realtime-preview-2025-06-03"
ASSISTANT_MODEL = "gpt-4o-mini-transcribe"

if not OPENAI_API_KEY:
    raise SystemExit("Please set OPENAI_API_KEY environment variable.")

app = Flask(__name__)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@app.route("/")
def index():
    """Serves a single-page HTML client that records mic → OpenAI Realtime API"""
    html = f"""\
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>Realtime Conversation (WebRTC + OpenAI)</title>
      <style>
        body {{ font-family: system-ui, sans-serif; margin: 40px; }}
        button {{ padding: 10px 16px; margin-right: 12px; }}
        #log {{ white-space: pre-wrap; border: 1px solid #ddd; padding: 12px;
                height: 360px; overflow: auto; }}
        .row {{ margin: 10px 0; }}
        .tag {{ display:inline-block; background:#f2f4f7; border:1px solid #e5e7eb;
                padding:2px 8px; border-radius:999px; font-size:12px; }}
      </style>
    </head>
    <body>
      <h2>Realtime Conversation (WebRTC → OpenAI)</h2>
      <div class="row">
        <button id="startBtn">Start mic + connect</button>
        <button id="stopBtn" disabled>Stop</button>
        <span class="tag">realtime model: {REALTIME_MODEL}</span>
        <span class="tag">assistant model: {ASSISTANT_MODEL}</span>
      </div>
      <div id="log"></div>

      <script>
        const logEl = document.getElementById("log");
        const startBtn = document.getElementById("startBtn");
        const stopBtn = document.getElementById("stopBtn");

        let pc = null;
        let dc = null;
        let localStream = null;

        function log(line) {{
          logEl.textContent += line + "\\n";
          logEl.scrollTop = logEl.scrollHeight;
        }}

        async function createSessionEphemeralKey() {{
          const r = await fetch("/session");
          if (!r.ok) {{
            throw new Error("Failed to mint ephemeral token: " + await r.text());
          }}
          const data = await r.json();
          return data.client_secret.value; // ephemeral key
        }}

        async function connect() {{
          const EPHEMERAL_KEY = await createSessionEphemeralKey();

          pc = new RTCPeerConnection();

          // create data channel
          dc = pc.createDataChannel("oai-events");
        

        // let userOutput = "";
        //let modelOutput = "";

dc.onmessage = (e) => {{
    try {{
        const msg = JSON.parse(e.data);

        // --- User speech partial ---
        // if (msg.type === "conversation.item.input_audio_transcription.delta" && msg.delta) {{
           //  userOutput += msg.delta;
            //log("You (partial): " + userOutput);
        // }}

        // --- User speech final ---
        if (msg.type === "conversation.item.input_audio_transcription.completed" && msg.transcript) {{
           log("You (final): " + msg.transcript);
           // userOutput = ""; // reset for next utterance
        }}

        // --- Model incremental audio transcript ---
      //  if (msg.type === "response.audio_transcript.delta" && msg.delta) {{
        //    modelOutput += msg.delta;
          // log("Model (partial): " + modelOutput);
        //}}

        // --- Model final transcript ---
        if (msg.type === "response.audio_transcript.done" && msg.transcript) {{
           log("Model (final): " + msg.transcript);
            modelOutput = ""; // reset for next response
           log("----");
        }}

        // --- Model text deltas (if used) ---
       // if (msg.type === "response.output_text.delta" && msg.delta) {{
         //  log("Model text delta: " + msg.delta);
        //}}

        if (msg.type === "response.completed") {{
           log("___----");
        }}

    }} catch (_) {{
       log("Non-JSON message:", e.data);
    }}
}};

          // wait for channel open before sending config
          dc.onopen = () => {{
            const sessionConfig = {{
              type: "session.update",
              session: {{
                input_audio_transcription:'${{ model: {ASSISTANT_MODEL} }}',
                turn_detection: {{
                  type: "server_vad",
                  threshold: 0.5,
                  prefix_padding_ms: 300,
                  silence_duration_ms: 500
                }},
                instructions: "You are a helpful AI assistant. Respond briefly. in english"
              }}
            }};
            dc.send(JSON.stringify(sessionConfig));
            log("Connected. Speak into your mic to see live transcripts + model replies.");
          }};

          // add mic track
          localStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
          localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

          // remote audio playback (if model outputs voice)
          const audioEl = document.createElement("audio");
          audioEl.autoplay = true;
          pc.ontrack = (e) => audioEl.srcObject = e.streams[0];

          // create offer
          const offer = await pc.createOffer({{ offerToReceiveAudio: true }});
          await pc.setLocalDescription(offer);

          // send offer to OpenAI Realtime API
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
          try {{
            await connect();
            stopBtn.disabled = false;
          }} catch (err) {{
            log("Error: " + err.message);
            startBtn.disabled = false;
          }}
        }};

        stopBtn.onclick = () => {{
          stopBtn.disabled = true;
          if (dc) dc.close();
          if (pc) pc.close();
          if (localStream) localStream.getTracks().forEach(t => t.stop());
          log("Stopped.");
          startBtn.disabled = false;
        }};
      </script>
    </body>
    </html>
    """
    return Response(textwrap.dedent(html), mimetype="text/html")


@app.route("/session", methods=["GET"])
def create_session():
    """Mint an ephemeral OpenAI Realtime key (valid ~1 min)."""
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    payload = {
        "model": REALTIME_MODEL,
        "modalities": ["audio", "text"],
        "voice": "verse",  # include voice if you also want spoken replies
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return jsonify(r.json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
