# frontend/app.py

import asyncio
import json
import logging
import tempfile
import os
import websockets

import streamlit as st
import streamlit.components.v1 as components

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Suporte Técnico por Voz",
    page_icon="🎙️",
    layout="centered",
)

st.title("🎙️ Assistente de Suporte Técnico")
st.caption("Grave sua pergunta e envie para o assistente.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_response" not in st.session_state:
    st.session_state.current_response = ""

response_placeholder = st.empty()
status_placeholder = st.empty()

st.subheader("Digite sua pergunta")

with st.form("text_query_form", clear_on_submit=True):
    text_input = st.text_input(
        "Pergunta",
        placeholder="Ex: Por que o sistema usa WebSocket?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Enviar", use_container_width=True)

if submitted and text_input.strip():
    st.session_state.messages.append({
        "role": "user",
        "content": text_input,
    })

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
                status_placeholder.info("⏳ Gerando resposta...")
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
                        st.session_state.current_response = response_text
                        status_placeholder.success("✅ Resposta completa")
                        break
                    elif msg["type"] == "error":
                        status_placeholder.error(msg.get("message"))
                        break
        except Exception as e:
            status_placeholder.error(f"Erro: {e}")

    asyncio.run(send_text_query(text_input))

# ──────────────────────────────────────────────
# Áudio — upload de arquivo gravado
# ──────────────────────────────────────────────
st.divider()
st.subheader("Ou envie um áudio")
st.caption("Grave com o gravador do seu sistema e faça upload do arquivo.")

audio_file = st.file_uploader(
    "Arquivo de áudio",
    type=["wav", "mp3", "ogg", "webm", "m4a"],
    label_visibility="collapsed",
)

if audio_file and st.button("📤 Transcrever e perguntar", use_container_width=True):
    status_placeholder.info("⏳ Enviando áudio para transcrição...")

    # Salva temporariamente
    suffix = os.path.splitext(audio_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name

    try:
        import requests
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                "http://localhost:8000/transcribe",
                files={"file": (audio_file.name, f, audio_file.type)},
            )
        if resp.status_code == 200:
            transcript = resp.json().get("transcript", "")
            if transcript:
                status_placeholder.info(f"🗣️ Você disse: {transcript}")
                st.session_state.messages.append({
                    "role": "user",
                    "content": transcript,
                })

                async def send_transcribed(text: str):
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
                                    response_placeholder.markdown(
                                        response_text + "▌"
                                    )
                                elif msg["type"] == "done":
                                    response_placeholder.markdown(response_text)
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": response_text,
                                    })
                                    status_placeholder.success("✅ Resposta completa")
                                    break
                                elif msg["type"] == "error":
                                    status_placeholder.error(msg.get("message"))
                                    break
                    except Exception as e:
                        status_placeholder.error(f"Erro: {e}")

                asyncio.run(send_transcribed(transcript))
            else:
                status_placeholder.warning("Não foi possível transcrever o áudio.")
        else:
            status_placeholder.error(f"Erro na transcrição: {resp.text}")
    finally:
        os.unlink(tmp_path)

# ──────────────────────────────────────────────
# Histórico
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