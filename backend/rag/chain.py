import logging
from typing import AsyncIterator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory

from backend.config import settings
from backend.rag.retriever import get_retriever
from backend.rag.prompts import RAG_PROMPT, CONDENSE_QUESTION_PROMPT

logger = logging.getLogger(__name__)


_session_store: dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> ChatMessageHistory:

    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
        logger.info(f"[Memory] Nova sessão criada: {session_id}")
    return _session_store[session_id]


def _build_llm() -> ChatOpenAI:

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        temperature=0.3,        
        max_tokens=256,         
        streaming=True,         
        model_kwargs={
            # Headers exigidos pelo OpenRouter para identificar a aplicação
            "extra_headers": {
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Voice RAG Support",
            }
        },
    )


def _format_docs(docs) -> str:

    if not docs:
        return "Nenhum documento relevante encontrado na base de conhecimento."

    chunks = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "desconhecido")
        chunks.append(
            f"[Trecho {i} — fonte: {source}]\n{doc.page_content}"
        )
    return "\n\n".join(chunks)


def get_rag_chain():

    llm = _build_llm()
    retriever = get_retriever()
    condense_chain = (
        CONDENSE_QUESTION_PROMPT
        | llm
        | StrOutputParser()
    )

    def condense_question(inputs: dict) -> str:

        if inputs.get("chat_history"):
            return condense_chain.invoke(inputs)
        return inputs["question"]


    def retrieve_and_format(inputs: dict) -> dict:
        condensed = condense_question(inputs)
        docs = retriever.invoke(condensed)
        return {
            "context": _format_docs(docs),
            "question": inputs["question"],
            "chat_history": inputs.get("chat_history", []),
        }


    core_chain = (
        RunnableLambda(retrieve_and_format)
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    chain_with_memory = RunnableWithMessageHistory(
        core_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
    )

    logger.info("[RAG] Chain montada com sucesso.")
    return chain_with_memory


async def stream_response(
    chain,
    question: str,
    session_id: str,
) -> AsyncIterator[str]:

    config = {"configurable": {"session_id": session_id}}

    async for token in chain.astream(
        {"question": question},
        config=config,
    ):
        if token:
            yield token