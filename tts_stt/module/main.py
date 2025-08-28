from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from stt_module import STTService
from tts_module import TTSService
import asyncio

app = FastAPI()
tts_service = TTSService()

@app.get("/")
async def index():
    with open("index.html") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def send_text_to_frontend(text):
        await websocket.send_text(text)

    stt_service = STTService()
    
    loop = asyncio.get_event_loop()
    
    # Run STT in background to push text to frontend
    def stt_callback(text):
        asyncio.run_coroutine_threadsafe(send_text_to_frontend(text), loop)

    try:
        # Start listening (blocking call) in a separate thread
        import threading
        threading.Thread(target=stt_service.start_listening, args=(stt_callback,), daemon=True).start()

        while True:
            data = await websocket.receive_text()
            # Whatever text comes from frontend, speak it
            tts_service.speak([data])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()
