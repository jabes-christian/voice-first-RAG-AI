import base64
import json
import logging
import queue
import sys
from pathlib import Path

import numpy as np
import asyncio
import websockets
from websockets.asyncio.client import connect

sys.path.append(str(Path(__file__).parent.parent))
from backend.speech.audio_utils import convert_to_pcm16k, chunk_audio

logger = logging.getLogger(__name__)

WS_URL = "ws://localhost:8000/ws/voice"


def get_audio_processor(audio_queue: queue.Queue):
    class AudioProcessor:
        def recv(self, frame):
            try:
                audio = frame.to_ndarray()
                if audio.ndim > 1:
                    audio = audio.mean(axis=0)
                audio_int16 = audio.astype(np.int16)
                raw_bytes = audio_int16.tobytes()
                pcm_bytes = convert_to_pcm16k(raw_bytes, frame.sample_rate)
                for chunk in chunk_audio(pcm_bytes):
                    try:
                        audio_queue.put_nowait(chunk)
                    except queue.Full:
                        pass
            except Exception as e:
                logger.error(f"[AudioProcessor] {e}")
            return frame

    return AudioProcessor


async def send_audio_and_receive(
    audio_queue: queue.Queue,
    result_queue: queue.Queue,
):
    try:
        async with connect(WS_URL) as ws:
            result_queue.put(("status", "🎙️ Conectado — pode falar!"))
            response_text = ""

            async def send_loop():
                loop = asyncio.get_event_loop()
                while True:
                    chunk = await loop.run_in_executor(None, audio_queue.get)
                    if chunk is None:
                        await ws.send(json.dumps({"type": "end_stream"}))
                        break
                    encoded = base64.b64encode(chunk).decode("utf-8")
                    await ws.send(json.dumps({
                        "type": "audio_chunk",
                        "data": encoded,
                    }))

            async def receive_loop():
                nonlocal response_text
                async for raw in ws:
                    msg = json.loads(raw)
                    msg_type = msg.get("type")

                    if msg_type == "transcript":
                        result_queue.put(("transcript", msg["text"]))
                    elif msg_type == "token":
                        response_text += msg["text"]
                        result_queue.put(("token", response_text))
                    elif msg_type == "done":
                        result_queue.put(("done", response_text))
                        response_text = ""
                    elif msg_type == "error":
                        result_queue.put(("error", msg.get("message", "")))

            await asyncio.gather(send_loop(), receive_loop())

    except Exception as e:
        logger.error(f"[WS Frontend] {e}")
        result_queue.put(("error", str(e)))