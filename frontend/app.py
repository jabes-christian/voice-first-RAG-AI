import asyncio
import json
import logging
import threading

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from audio_recorder import get_audio_processor, send_audio_and_receive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Suporte Técnico por Voz",
    page_icon="🎙️",
    layout="centered",
)

st.title("🎙️ Assistente de Suporte Técnico")
st.caption("Fale sua dúvida — o assistente responde em tempo real.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "ws_queue" not in st.session_state:

    st.session_state.ws_queue = asyncio.Queue(maxsize=100)

if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None


status_placeholder = st.empty()
transcript_placeholder = st.empty()
response_placeholder = st.empty()


st.subheader("Captura de voz")

AudioProcessor = get_audio_processor(st.session_state.ws_queue)

ctx = webrtc_streamer(
    key="voice-rag",
    mode=WebRtcMode.SENDONLY,
    audio_receiver_size=1024,
    media_stream_constraints={
        "audio": {
            "echoCancellation": True,
            "noiseSuppression": True,
            "sampleRate": 16000,
        },
        "video": False,
    },
    audio_frame_callback=AudioProcessor().recv,
    async_processing=True,
)

def run_ws_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        send_audio_and_receive(
            ws_queue=st.session_state.ws_queue,
            transcript_placeholder=transcript_placeholder,
            response_placeholder=response_placeholder,
            status_placeholder=status_placeholder,
        )
    )


if ctx.state.playing:
    if (
        st.session_state.ws_thread is None
        or not st.session_state.ws_thread.is_alive()
    ):
        status_placeholder.info("🔄 Conectando ao backend...")
        ws_thread = threading.Thread(target=run_ws_loop, daemon=True)
        ws_thread.start()
        st.session_state.ws_thread = ws_thread
else:
    # Stream parado — sinaliza fim para o WebSocket
    if not st.session_state.ws_queue.empty():
        st.session_state.ws_queue.put_nowait(None)
    status_placeholder.warning("⏸️ Microfone pausado")


st.divider()
st.subheader("Ou digite sua pergunta")

with st.form("text_query_form", clear_on_submit=True):
    text_input = st.text_input(
        "Pergunta",
        placeholder="Ex: Como configurar o Azure Speech SDK?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Enviar", use_container_width=True)

if submitted and text_input.strip():
    st.session_state.messages.append({
        "role": "user",
        "content": text_input,
    })

    import websockets
    import asyncio as _asyncio

    async def send_text_query(text: str):
        try:
            async with websockets.connect("ws://localhost:8000/ws/voice") as ws:
                await ws.send(json.dumps({
                    "type": "text_query",
                    "text": text,
                }))
                response_text = ""
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg["type"] == "token":
                        response_text += msg["text"]
                        response_placeholder.markdown(response_text + "▌")
                    elif msg["type"] == "done":
                        response_placeholder.markdown(response_text)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response_text,
                        })
                        break
                    elif msg["type"] == "error":
                        st.error(msg.get("message"))
                        break
        except Exception as e:
            st.error(f"Erro ao conectar: {e}")

    _asyncio.run(send_text_query(text_input))

if st.session_state.messages:
    st.divider()
    st.subheader("Histórico")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])

    if st.button("🗑️ Limpar histórico"):
        st.session_state.messages = []
        st.rerun()