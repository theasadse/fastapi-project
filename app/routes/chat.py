from fastapi import APIRouter, Depends, status
import logging
import time
import uuid
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from pinecone import Pinecone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMemoryReadResponse,
    ChatSemanticMemorySearchRequest,
    ChatSemanticMemorySearchResponse,
    ChatSemanticMemoryUpsertRequest,
    ChatMemoryUpsertRequest,
    ChatMessageRead,
    ChatRequest,
    ChatResponse,
)
from app.services.chat import chat_memory_service
from app.services.chat_cache import CachedChatMessage, chat_cache_service

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])
logger = logging.getLogger(__name__)

chat_cache_service.per_session_limit = settings.chat_cache_session_message_limit
chat_cache_service.max_sessions = settings.chat_cache_max_sessions
chat_cache_service.session_ttl_seconds = settings.chat_cache_session_ttl_seconds
redis_enabled = chat_cache_service.configure_redis(
    redis_url=settings.redis_url,
    key_prefix=settings.chat_cache_key_prefix,
)

# Initialize the LLM here so it's loaded once and ready for requests
llm = Ollama(model="mistral")
embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")
logger.info("chat.model_initialized model=mistral provider=ollama")
logger.info("chat.embedding_model_initialized model=mxbai-embed-large")
logger.info("chat.cache_backend backend=%s", "redis" if redis_enabled else "in-memory")


def _flush_pending_batch(db: Session, max_items: int) -> int:
    pending = chat_cache_service.pop_pending_batch(max_items=max_items)
    if not pending:
        return 0

    items = [(item.session_id, item.role, item.message) for item in pending]
    return chat_memory_service.add_messages_bulk(db, items)


def _flush_session_pending(db: Session, session_id: str) -> int:
    pending = chat_cache_service.pop_session_pending(session_id=session_id)
    if not pending:
        return 0

    items = [(item.session_id, item.role, item.message) for item in pending]
    return chat_memory_service.add_messages_bulk(db, items)


def _semantic_namespace(session_id: str) -> str:
    return f"{settings.chat_semantic_namespace_prefix}:{session_id}"


def _is_important_memory(text: str) -> bool:
    normalized = text.lower().strip()
    if len(normalized) < 10:
        return False

    important_markers = [
        "my name is",
        "i am",
        "i'm",
        "remember",
        "my preference",
        "i prefer",
        "my goal",
        "i want",
        "my company",
        "my project",
    ]
    return any(marker in normalized for marker in important_markers)


def _get_pinecone_index():
    if not settings.pinecone_api_key:
        return None

    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)


def _extract_memory_texts(search_results: object) -> list[str]:
    if isinstance(search_results, dict):
        matches = search_results.get("matches", [])
    else:
        matches = getattr(search_results, "matches", [])

    snippets: list[str] = []
    for match in matches:
        if isinstance(match, dict):
            metadata = match.get("metadata") or {}
        else:
            metadata = getattr(match, "metadata", {}) or {}

        text = metadata.get("text")
        if isinstance(text, str) and text.strip():
            snippets.append(text.strip())
    return snippets


def _search_semantic_memory(session_id: str, query: str, top_k: int) -> list[str]:
    index = _get_pinecone_index()
    if index is None:
        return []

    query_vector = embeddings_model.embed_query(query)
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        namespace=_semantic_namespace(session_id),
    )
    return _extract_memory_texts(results)


def _store_semantic_memory(session_id: str, text: str, source: str) -> bool:
    index = _get_pinecone_index()
    if index is None:
        return False

    vector = embeddings_model.embed_query(text)
    index.upsert(
        vectors=[
            {
                "id": str(uuid.uuid4()),
                "values": vector,
                "metadata": {"text": text, "source": source},
            }
        ],
        namespace=_semantic_namespace(session_id),
    )
    return True

@router.post("/", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Receives a message from the frontend, sends it to Mistral via LangChain, and returns the response.
    """
    request_id = str(uuid.uuid4())[:8]
    session_id = payload.session_id or str(uuid.uuid4())
    started_at = time.perf_counter()
    logger.info(
        "chat.request_received request_id=%s session_id=%s message_chars=%d",
        request_id,
        session_id,
        len(payload.message),
    )

    recent_messages = chat_cache_service.get_recent_messages(session_id=session_id, limit=12)
    memory_source = "cache"
    if not recent_messages:
        db_recent_messages = chat_memory_service.get_recent_messages(db, session_id=session_id, limit=12)
        warm_items = [
            CachedChatMessage(session_id=session_id, role=item.role, message=item.message)
            for item in db_recent_messages
        ]
        chat_cache_service.warm_session(session_id=session_id, messages=warm_items)
        recent_messages = chat_cache_service.get_recent_messages(session_id=session_id, limit=12)
        memory_source = "database"

    memory_count = len(recent_messages)
    long_term_memory = chat_memory_service.get_long_term_memory(db, session_id=session_id)
    long_term_memory_text = long_term_memory.memory if long_term_memory is not None else ""
    semantic_memories: list[str] = []
    try:
        semantic_memories = _search_semantic_memory(
            session_id=session_id,
            query=payload.message,
            top_k=settings.chat_semantic_top_k,
        )
    except Exception as semantic_error:
        logger.warning(
            "chat.semantic_memory.search_failed request_id=%s session_id=%s reason=%s",
            request_id,
            session_id,
            semantic_error,
        )

    logger.info(
        "chat.memory.loaded request_id=%s session_id=%s source=%s memory_messages=%d long_term_memory=%s semantic_memories=%d",
        request_id,
        session_id,
        memory_source,
        memory_count,
        bool(long_term_memory_text),
        len(semantic_memories),
    )

    prompt_parts: list[str] = [
        "You are a helpful AI assistant. Keep context from long-term and conversation history.",
    ]
    if long_term_memory_text:
        prompt_parts.extend([
            "Long-term memory:",
            long_term_memory_text,
        ])

    if semantic_memories:
        prompt_parts.append("Relevant semantic memories:")
        for snippet in semantic_memories:
            prompt_parts.append(f"- {snippet}")

    prompt_parts.extend([
        "Conversation history:",
    ])
    for item in recent_messages:
        role_label = "User" if item.role == "user" else "Assistant"
        prompt_parts.append(f"{role_label}: {item.message}")

    prompt_parts.append(f"User: {payload.message}")
    prompt_parts.append("Assistant:")
    prompt = "\n".join(prompt_parts)

    # Simply invoke the model with the user's string message
    logger.info("chat.llm_invoke.begin request_id=%s session_id=%s", request_id, session_id)
    ai_response = llm.invoke(prompt)

    chat_cache_service.add_message(session_id=session_id, role="user", message=payload.message)
    chat_cache_service.add_message(session_id=session_id, role="assistant", message=ai_response)

    pending_count = chat_cache_service.pending_count()
    if pending_count >= settings.chat_cache_flush_batch_size:
        flushed_count = _flush_pending_batch(db, settings.chat_cache_flush_batch_size)
        logger.info(
            "chat.cache.flush_triggered request_id=%s session_id=%s flushed=%d pending_after=%d",
            request_id,
            session_id,
            flushed_count,
            chat_cache_service.pending_count(),
        )

    if _is_important_memory(payload.message):
        try:
            stored = _store_semantic_memory(
                session_id=session_id,
                text=payload.message,
                source="user_message",
            )
            logger.info(
                "chat.semantic_memory.saved request_id=%s session_id=%s stored=%s",
                request_id,
                session_id,
                stored,
            )
        except Exception as semantic_store_error:
            logger.warning(
                "chat.semantic_memory.save_failed request_id=%s session_id=%s reason=%s",
                request_id,
                session_id,
                semantic_store_error,
            )

    logger.info(
        "chat.memory.saved request_id=%s session_id=%s saved_messages=2",
        request_id,
        session_id,
    )

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "chat.llm_invoke.success request_id=%s session_id=%s latency_ms=%s response_chars=%d",
        request_id,
        session_id,
        elapsed_ms,
        len(ai_response),
    )

    # Return the AI's response to the frontend client
    return ChatResponse(
        reply=ai_response,
        session_id=session_id,
        memory_messages_used=memory_count,
        long_term_memory_used=bool(long_term_memory_text),
        semantic_memories_used=len(semantic_memories),
    )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str, db: Session = Depends(get_db)) -> ChatHistoryResponse:
    _flush_session_pending(db, session_id=session_id)
    messages = chat_memory_service.get_all_messages(db, session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatMessageRead(role=item.role, message=item.message) for item in messages],
    )


@router.delete("/history/{session_id}", status_code=status.HTTP_200_OK)
def clear_chat_history(session_id: str, db: Session = Depends(get_db)) -> dict[str, int | str]:
    _flush_session_pending(db, session_id=session_id)
    deleted_count = chat_memory_service.clear_session(db, session_id)
    chat_cache_service.clear_session(session_id=session_id)
    return {"session_id": session_id, "deleted_messages": deleted_count}


@router.put("/memory/{session_id}", response_model=ChatMemoryReadResponse)
def upsert_long_term_memory(
    session_id: str,
    payload: ChatMemoryUpsertRequest,
    db: Session = Depends(get_db),
) -> ChatMemoryReadResponse:
    memory = chat_memory_service.set_long_term_memory(
        db,
        session_id=session_id,
        memory=payload.memory,
    )
    logger.info("chat.long_term_memory.saved session_id=%s", session_id)
    return ChatMemoryReadResponse(session_id=memory.session_id, memory=memory.memory)


@router.get("/memory/{session_id}", response_model=ChatMemoryReadResponse)
def get_long_term_memory(session_id: str, db: Session = Depends(get_db)) -> ChatMemoryReadResponse:
    memory = chat_memory_service.get_long_term_memory(db, session_id=session_id)
    if memory is None:
        return ChatMemoryReadResponse(session_id=session_id, memory="")
    return ChatMemoryReadResponse(session_id=memory.session_id, memory=memory.memory)


@router.delete("/memory/{session_id}", status_code=status.HTTP_200_OK)
def clear_long_term_memory(session_id: str, db: Session = Depends(get_db)) -> dict[str, int | str]:
    deleted = chat_memory_service.clear_long_term_memory(db, session_id=session_id)
    logger.info("chat.long_term_memory.cleared session_id=%s deleted=%s", session_id, deleted)
    return {"session_id": session_id, "deleted": int(deleted)}


@router.put("/memory/semantic/{session_id}", status_code=status.HTTP_200_OK)
def upsert_semantic_memory(
    session_id: str,
    payload: ChatSemanticMemoryUpsertRequest,
) -> dict[str, int | str]:
    stored = _store_semantic_memory(
        session_id=session_id,
        text=payload.memory,
        source="manual",
    )
    logger.info("chat.semantic_memory.manual_saved session_id=%s stored=%s", session_id, stored)
    return {"session_id": session_id, "stored": int(stored)}


@router.post("/memory/semantic/{session_id}/search", response_model=ChatSemanticMemorySearchResponse)
def search_semantic_memory(
    session_id: str,
    payload: ChatSemanticMemorySearchRequest,
) -> ChatSemanticMemorySearchResponse:
    memories = _search_semantic_memory(
        session_id=session_id,
        query=payload.query,
        top_k=payload.top_k,
    )
    return ChatSemanticMemorySearchResponse(
        session_id=session_id,
        query=payload.query,
        memories=memories,
    )
