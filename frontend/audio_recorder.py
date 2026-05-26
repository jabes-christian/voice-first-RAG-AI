import asyncio
import base64
import json
import logging
import sys
from pathlib import Path

import numpy as np
import streamlit as st
import websockets
from streamlit_webrtc import WebRtcMode, webrtc_streamer
import av

sys.path.append(str(Path(__file__).parent.parent))
from backend.speech.audio_utils import convert_to_pcm16k, chunk_audio

logger = logging.getLogger(__name__)

WS_URL = "ws://localhost:8000/ws/voice"


def get_audio_processor(ws_queue: asyncio.Queue):
    """
    Retorna um processador de frames de áudio compatível com
    o streamlit-webrtc.

    Cada frame de áudio capturado pelo WebRTC é:
    1. Convertido de float32 → int16
    2. Reamostrado para 16kHz mono (formato Azure)
    3. Dividido em chunks de 100ms
    4. Enfileirado para envio via WebSocket
    """

    class AudioProcessor:
        def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
            audio = frame.to_ndarray()

            if audio.ndim > 1:
                audio = audio.mean(axis=0)

            audio_int16 = audio.astype(np.int16)
            raw_bytes = audio_int16.tobytes()

            source_rate = frame.sample_rate
            pcm_bytes = convert_to_pcm16k(raw_bytes, source_rate)

            for chunk in chunk_audio(pcm_bytes):
                try:
                    ws_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    pass

            return frame

    return AudioProcessor


async def send_audio_and_receive(
    ws_queue: asyncio.Queue,
    transcript_placeholder,
    response_placeholder,
    status_placeholder,
):
    """
    Conecta ao WebSocket do FastAPI, envia chunks de áudio
    e recebe transcrições + tokens de resposta em tempo real.

    Protocolo de mensagens:
      → { type: audio_chunk, data: <base64> }
      ← { type: transcript, text: "..." }
      ← { type: token,      text: "..." }
      ← { type: done }
      ← { type: error,      message: "..." }
    """
    try:
        async with websockets.connect(WS_URL) as ws:
            status_placeholder.info("🎙️ Conectado — pode falar!")
            response_text = ""

            async def send_loop():
                while True:
                    chunk = await ws_queue.get()
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
                        transcript_placeholder.info(
                            f"🗣️ **Você disse:** {msg['text']}"
                        )

                    elif msg_type == "token":
                        response_text += msg["text"]
                        response_placeholder.markdown(response_text + "▌")

                    elif msg_type == "done":
                        response_placeholder.markdown(response_text)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response_text,
                        })
                        response_text = ""
                        status_placeholder.success("✅ Resposta completa")

                    elif msg_type == "error":
                        status_placeholder.error(
                            f"❌ Erro: {msg.get('message')}"
                        )

            await asyncio.gather(send_loop(), receive_loop())

    except Exception as e:
        status_placeholder.error(f"❌ Falha na conexão WebSocket: {e}")
        logger.error(f"[WS Frontend] {e}")