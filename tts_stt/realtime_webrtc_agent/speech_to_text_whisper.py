from flask import Flask, request, render_template_string, jsonify
import openai
import tempfile
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# HTML frontend with continuous recording
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>Whisper STT</title>
</head>
<body>
  <h2>Speech to Text with Whisper</h2>
  <button id="startBtn">Start Recording</button>
  <button id="stopBtn">Stop Recording</button>
  <p><strong>Transcript:</strong></p>
  <pre id="output"></pre>

  <script>
    let mediaRecorder;
    let audioChunks = [];

    document.getElementById("startBtn").onclick = async () => {
      let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append("file", audioBlob, "audio.webm");

        const res = await fetch("/transcribe", {
          method: "POST",
          body: formData
        });

        if (!res.ok) {
          document.getElementById("output").innerText = "Error: " + res.statusText;
          return;
        }

        const data = await res.json();
        document.getElementById("output").innerText = data.text;
      };

      mediaRecorder.start();
    };

    document.getElementById("stopBtn").onclick = () => {
      mediaRecorder.stop();
    };
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        file.save(tmp.name)
        tmp.flush()

        with open(tmp.name, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        os.unlink(tmp.name)

    return jsonify({"text": transcript.text})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
