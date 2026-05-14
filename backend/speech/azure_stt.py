import asyncio
import logging
from typing import AsyncGenerator

import azure.cognitiveservices.speech as speechsdk

from backend.config import settings

logger = logging.getLogger(__name__)


class AzureSTTClient:


    def __init__(self, session_id: str):
        self.session_id = session_id
        self._recognizer: speechsdk.SpeechRecognizer | None = None
        self._push_stream: speechsdk.audio.PushAudioInputStream | None = None

        self._transcript_queue: asyncio.Queue[str | None] = asyncio.Queue()

        self._loop = asyncio.get_event_loop()

    # ──────────────────────────────────────────────
    # Setup do recognizer
    # ──────────────────────────────────────────────
    def _build_recognizer(self) -> speechsdk.SpeechRecognizer:

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION,
        )

        speech_config.speech_recognition_language = "pt-BR"

        speech_config.set_profanity(speechsdk.ProfanityOption.Masked)

        speech_config.output_format = speechsdk.OutputFormat.Simple

        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000,
            bits_per_sample=16,
            channels=1,
        )
        self._push_stream = speechsdk.audio.PushAudioInputStream(
            stream_format=audio_format
        )
        audio_config = speechsdk.audio.AudioConfig(
            stream=self._push_stream
        )

        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        self._register_callbacks(recognizer)
        return recognizer

    # ──────────────────────────────────────────────
    # Callbacks do SDK (rodam em threads C++ do SDK)
    # ──────────────────────────────────────────────
    def _register_callbacks(self, recognizer: speechsdk.SpeechRecognizer):

        def _put(item: str | None):
            self._loop.call_soon_threadsafe(
                self._transcript_queue.put_nowait, item
            )

        def on_recognized(evt: speechsdk.SpeechRecognitionEventArgs):

            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = evt.result.text.strip()
                if text:
                    logger.info(
                        f"[STT:{self.session_id}] Reconhecido: '{text}'"
                    )
                    _put(text)
            elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                logger.debug(
                    f"[STT:{self.session_id}] Sem match: "
                    f"{evt.result.no_match_details}"
                )

        def on_canceled(evt: speechsdk.SpeechRecognitionCanceledEventArgs):

            if evt.reason == speechsdk.CancellationReason.Error:
                logger.error(
                    f"[STT:{self.session_id}] Erro Azure: "
                    f"code={evt.error_code} details={evt.error_details}"
                )
            _put(None)

        def on_session_stopped(evt):

            logger.info(f"[STT:{self.session_id}] Sessão encerrada.")
            _put(None)

        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)
        recognizer.session_stopped.connect(on_session_stopped)

    # ──────────────────────────────────────────────
    # Interface pública — usada pelo main.py
    # ──────────────────────────────────────────────
    async def stream_transcription(
        self,
        audio_queue: asyncio.Queue[bytes | None],
    ) -> AsyncGenerator[str, None]:

        self._recognizer = await asyncio.to_thread(self._build_recognizer)
        await asyncio.to_thread(
            self._recognizer.start_continuous_recognition
        )
        logger.info(
            f"[STT:{self.session_id}] Reconhecimento contínuo iniciado."
        )

        async def _push_audio():

            while True:
                chunk = await audio_queue.get()
                if chunk is None:

                    self._push_stream.close()
                    logger.info(
                        f"[STT:{self.session_id}] PushStream fechado."
                    )
                    break
                self._push_stream.write(chunk)

        push_task = asyncio.create_task(_push_audio())

        try:
            while True:
                transcript = await self._transcript_queue.get()
                if transcript is None:
                    break 
                yield transcript
        finally:
            push_task.cancel()
            try:
                await push_task
            except asyncio.CancelledError:
                pass

    async def close(self):

        if self._recognizer:
            await asyncio.to_thread(
                self._recognizer.stop_continuous_recognition
            )
            self._recognizer = None
            logger.info(
                f"[STT:{self.session_id}] Recognizer encerrado."
            )