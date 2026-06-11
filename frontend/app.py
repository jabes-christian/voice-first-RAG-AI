# frontend/app.py

import asyncio
import json
import logging
import queue
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

# ──────────────────────────────────────────────
# Estado da sessão
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "audio_queue" not in st.session_state:
    st.session_state.audio_queue = queue.Queue(maxsize=500)

if "result_queue" not in st.session_state:
    st.session_state.result_queue = queue.Queue()

if "ws_thread" not in st.session_state:
    st.session_state.ws_thread = None

# ──────────────────────────────────────────────
# Placeholders de UI
# ──────────────────────────────────────────────
status_placeholder = st.empty()
transcript_placeholder = st.empty()
response_placeholder = st.empty()

# ──────────────────────────────────────────────
# Referências locais às filas — ANTES de qualquer uso
# Declaradas aqui para estarem disponíveis em todo o script
# ──────────────────────────────────────────────
_audio_queue = st.session_state.audio_queue
_result_queue = st.session_state.result_queue

# ──────────────────────────────────────────────
# Captura de áudio via WebRTC
# ──────────────────────────────────────────────
st.subheader("Captura de voz")

AudioProcessor = get_audio_processor(_audio_queue)

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

# ──────────────────────────────────────────────
# Thread do WebSocket
# ──────────────────────────────────────────────
def run_ws_loop(audio_q: queue.Queue, result_q: queue.Queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            send_audio_and_receive(audio_q, result_q)
        )
    except Exception as e:
        logger.error(f"[WS Thread] {e}")
        result_q.put(("error", str(e)))
    finally:
        loop.close()


# ──────────────────────────────────────────────
# Controle do stream — APÓS declaração das filas
# ──────────────────────────────────────────────
if ctx.state.playing:
    if (
        st.session_state.ws_thread is None
        or not st.session_state.ws_thread.is_alive()
    ):
        status_placeholder.info("🔄 Conectando ao backend...")
        ws_thread = threading.Thread(
            target=run_ws_loop,
            args=(_audio_queue, _result_queue),
            daemon=True,
        )
        ws_thread.start()
        st.session_state.ws_thread = ws_thread

    # Lê resultados e atualiza UI no thread principal
    try:
        while True:
            msg_type, content = _result_queue.get_nowait()

            if msg_type == "status":
                status_placeholder.info(content)
            elif msg_type == "transcript":
                transcript_placeholder.info(f"🗣️ **Você disse:** {content}")
            elif msg_type == "token":
                response_placeholder.markdown(content + "▌")
            elif msg_type == "done":
                response_placeholder.markdown(content)
                if content:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                status_placeholder.success("✅ Resposta completa")
            elif msg_type == "error":
                status_placeholder.error(f"❌ {content}")

    except queue.Empty:
        pass

else:
    # Stream parado — esvazia fila e sinaliza fim
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break
    try:
        _audio_queue.put_nowait(None)
    except queue.Full:
        pass
    status_placeholder.warning("⏸️ Microfone pausado")

# ──────────────────────────────────────────────
# Fallback: entrada de texto manual
# ──────────────────────────────────────────────
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

    async def send_text_query(text: str):
        try:
            async with websockets.connect(
                "ws://localhost:8000/ws/voice"
            ) as ws:
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

    asyncio.run(send_text_query(text_input))

# ──────────────────────────────────────────────
# Histórico de conversa
# ──────────────────────────────────────────────
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