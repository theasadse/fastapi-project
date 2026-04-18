from fastapi import APIRouter, HTTPException
import logging
import time
import uuid
from pydantic import BaseModel
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from app.core.config import settings
from pinecone import Pinecone

router = APIRouter(prefix="/ai", tags=["AI & RAG"])
logger = logging.getLogger(__name__)


def _text_preview(text: str, max_chars: int = 120) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars]}..."


def _vector_sample(vector: list[float], size: int = 5) -> list[float]:
    return [round(value, 6) for value in vector[:size]]

class AskRequest(BaseModel):
    query: str

class IngestRequest(BaseModel):
    content: str

def get_pinecone_index():
    """
    Directly connects to Pinecone using the modern SDK.
    """
    if not settings.pinecone_api_key:
        raise HTTPException(status_code=500, detail="Pinecone API Key not configured")

    logger.debug("rag.pinecone.connect index=%s", settings.pinecone_index_name)
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)

@router.post("/ingest")
async def ingest_data(request: IngestRequest):
    """
    Ingest text into Pinecone using local embeddings.
    """
    try:
        request_id = str(uuid.uuid4())[:8]
        started_at = time.perf_counter()
        logger.info(
            "rag.ingest.request_received request_id=%s content_chars=%d",
            request_id,
            len(request.content),
        )

        # 1. Generate Embeddings locally
        logger.info("rag.ingest.embedding.begin request_id=%s model=mxbai-embed-large", request_id)
        logger.debug(
            "rag.ingest.embedding.input request_id=%s prompt_preview=%r chars=%d words=%d",
            request_id,
            _text_preview(request.content),
            len(request.content),
            len(request.content.split()),
        )
        embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")
        vector = embeddings_model.embed_query(request.content)
        logger.info(
            "rag.ingest.embedding.success request_id=%s vector_dimensions=%d",
            request_id,
            len(vector),
        )
        logger.debug(
            "rag.ingest.embedding.vector_sample request_id=%s sample=%s",
            request_id,
            _vector_sample(vector),
        )
        
        # 2. Get Pinecone Index
        logger.info(
            "rag.ingest.vector_db_connect.begin request_id=%s index=%s",
            request_id,
            settings.pinecone_index_name,
        )
        index = get_pinecone_index()
        logger.info("rag.ingest.vector_db_connect.success request_id=%s", request_id)
        
        # 3. Upsert into Pinecone
        vector_id = str(uuid.uuid4())
        logger.info("rag.ingest.upsert.begin request_id=%s vector_id=%s", request_id, vector_id)
        index.upsert(vectors=[{
            "id": vector_id,
            "values": vector,
            "metadata": {"text": request.content}
        }])

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "rag.ingest.completed request_id=%s latency_ms=%s",
            request_id,
            elapsed_ms,
        )

        return {"status": "success", "message": "Data ingested successfully"}
    except Exception as e:
        logger.exception("rag.ingest.failed error=%s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def ask_ai(request: AskRequest):
    """
    Ask a question using Manual RAG (Ollama + Pinecone Direct).
    """
    try:
        request_id = str(uuid.uuid4())[:8]
        started_at = time.perf_counter()
        logger.info(
            "rag.ask.request_received request_id=%s query_chars=%d",
            request_id,
            len(request.query),
        )

        # 1. Embed the user query
        logger.info("rag.ask.embedding.begin request_id=%s model=mxbai-embed-large", request_id)
        logger.debug(
            "rag.ask.embedding.input request_id=%s query_preview=%r chars=%d words=%d",
            request_id,
            _text_preview(request.query),
            len(request.query),
            len(request.query.split()),
        )
        embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")
        query_vector = embeddings_model.embed_query(request.query)
        logger.info(
            "rag.ask.embedding.success request_id=%s vector_dimensions=%d",
            request_id,
            len(query_vector),
        )
        logger.debug(
            "rag.ask.embedding.vector_sample request_id=%s sample=%s",
            request_id,
            _vector_sample(query_vector),
        )

        # 2. Search Pinecone for context (graceful fallback if unavailable)
        context_chunks: list[str] = []
        retrieval_note: str | None = None

        if settings.pinecone_api_key:
            try:
                logger.info(
                    "rag.ask.retrieve.begin request_id=%s top_k=3 index=%s",
                    request_id,
                    settings.pinecone_index_name,
                )
                index = get_pinecone_index()
                search_results = index.query(vector=query_vector, top_k=3, include_metadata=True)

                if isinstance(search_results, dict):
                    matches = search_results.get("matches", [])
                else:
                    matches = getattr(search_results, "matches", [])

                logger.info(
                    "rag.ask.retrieve.success request_id=%s match_count=%d",
                    request_id,
                    len(matches),
                )

                for match in matches:
                    if isinstance(match, dict):
                        metadata = match.get("metadata") or {}
                    else:
                        metadata = getattr(match, "metadata", {}) or {}

                    text = metadata.get("text")
                    if isinstance(text, str) and text.strip():
                        context_chunks.append(text.strip())
            except Exception as retrieval_error:
                retrieval_note = f"Pinecone retrieval failed, answered without RAG context: {retrieval_error}"
                logger.warning(
                    "rag.ask.retrieve.failed request_id=%s reason=%s",
                    request_id,
                    retrieval_error,
                )
        else:
            retrieval_note = "Pinecone API key not configured, answered without RAG context."
            logger.warning("rag.ask.retrieve.skipped request_id=%s reason=no_api_key", request_id)

        context = "\n".join(context_chunks)
        logger.info(
            "rag.ask.context_built request_id=%s used_rag_context=%s context_chunks=%d",
            request_id,
            bool(context),
            len(context_chunks),
        )

        # 3. Generate answer using local LLM
        llm = Ollama(model="mistral")
        logger.info("rag.ask.generation.begin request_id=%s model=mistral", request_id)

        if context:
            prompt = (
                "Use the following context to answer the question. "
                "If the answer is not in the context, say that clearly and then provide your best general answer."
                f"\n\nContext:\n{context}\n\nQuestion: {request.query}\n\nAnswer:"
            )
        else:
            prompt = (
                "No relevant context was retrieved from the vector database. "
                "Answer the question using general knowledge and clearly mention uncertainty when needed."
                f"\n\nQuestion: {request.query}\n\nAnswer:"
            )

        logger.debug(
            "rag.ask.generation.prompt request_id=%s prompt_chars=%d context_chars=%d",
            request_id,
            len(prompt),
            len(context),
        )

        response = llm.invoke(prompt)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "rag.ask.completed request_id=%s latency_ms=%s answer_chars=%d",
            request_id,
            elapsed_ms,
            len(response),
        )

        return {
            "query": request.query,
            "answer": response,
            "context_found": context if context else "",
            "used_rag_context": bool(context),
            "note": retrieval_note,
        }
    except Exception as e:
        logger.exception("rag.ask.failed error=%s", e)
        raise HTTPException(status_code=500, detail=str(e))
