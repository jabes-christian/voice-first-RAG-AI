import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.speech.azure_stt import AzureSTTClient
from backend.rag.chain import get_rag_chain


logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # session_id → WebSocket
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws
        logger.info(f"[WS] Sessão conectada: {session_id}")

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)
        logger.info(f"[WS] Sessão encerrada: {session_id}")

    async def send_json(self, session_id: str, payload: dict):
        """Envia um payload JSON para uma sessão específica."""
        ws = self.active.get(session_id)
        if ws:
            await ws.send_json(payload)

    async def send_text(self, session_id: str, text: str):
        ws = self.active.get(session_id)
        if ws:
            await ws.send_text(text)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando RAG chain...")
    app.state.rag_chain = await asyncio.to_thread(get_rag_chain)
    logger.info("RAG chain pronto.")
    yield
    logger.info("Encerrando aplicação.")


app = FastAPI(
    title="Voice RAG Support",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir em produção
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "rag_ready": hasattr(app.state, "rag_chain")}

# ──────────────────────────────────────────────
# WebSocket principal
# Protocolo de mensagens (JSON):
#
#  Cliente → Servidor:
#    { "type": "audio_chunk", "data": "<bytes_b64>" }
#    { "type": "end_stream" }
#    { "type": "text_query", "text": "..." }  ← fallback sem áudio
#
#  Servidor → Cliente:
#    { "type": "transcript",  "text": "..." }
#    { "type": "token",       "text": "..." }  ← streaming token a token
#    { "type": "done" }
#    { "type": "error",       "message": "..." }
# ──────────────────────────────────────────────

@app.websocket("/ws/voice")
async def voice_endpoint(ws: WebSocket):
    session_id = str(uuid.uuid4())
    await manager.connect(session_id, ws)

    # Instancia o cliente STT dedicado a esta sessão
    stt_client = AzureSTTClient(session_id=session_id)
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()

    # ── Task 1: Lê mensagens do WebSocket e roteia ──
    async def receive_loop():
        try:
            async for raw in ws.iter_text():
                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "audio_chunk":
                    # Decodifica Base64 → bytes e enfileira para o STT
                    import base64
                    chunk = base64.b64decode(msg["data"])
                    await audio_queue.put(chunk)

                elif msg_type == "end_stream":
                    # Sinaliza fim do stream de áudio
                    await audio_queue.put(None)

                elif msg_type == "text_query":
                    # Atalho: texto direto, pula STT
                    await process_query(msg["text"])

        except WebSocketDisconnect:
            logger.info(f"[WS] Cliente desconectou: {session_id}")
        finally:
            await audio_queue.put(None)  # Garante fim da fila

    # ── Task 2: Consome áudio → STT → RAG ──
    async def stt_and_rag_loop():
        async for transcript in stt_client.stream_transcription(audio_queue):
            if transcript:
                # Envia a transcrição para o cliente ver em tempo real
                await manager.send_json(session_id, {
                    "type": "transcript",
                    "text": transcript,
                })
                # Com a transcrição em mãos, dispara o RAG
                await process_query(transcript)

    # ── Processa uma query pela chain RAG com streaming ──
    async def process_query(query: str):
        try:
            chain = app.state.rag_chain

            # astream retorna tokens assim que ficam disponíveis
            async for token in chain.astream(
                {"question": query},
                config={"configurable": {"session_id": session_id}},
            ):
                await manager.send_json(session_id, {
                    "type": "token",
                    "text": token,
                })

            # Sinaliza ao frontend que a resposta terminou
            await manager.send_json(session_id, {"type": "done"})

        except Exception as e:
            logger.error(f"[RAG] Erro na sessão {session_id}: {e}")
            await manager.send_json(session_id, {
                "type": "error",
                "message": "Erro ao processar sua pergunta.",
            })

    # ── Executa as duas tasks em paralelo ──
    try:
        await asyncio.gather(
            receive_loop(),
            stt_and_rag_loop(),
        )
    except Exception as e:
        logger.exception(f"[WS] Erro não tratado na sessão {session_id}: {e}")
    finally:
        manager.disconnect(session_id)
        await stt_client.close()