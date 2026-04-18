from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_core.documents import Document
from app.core.config import settings
from pinecone import Pinecone
import os

router = APIRouter(prefix="/ai", tags=["AI & RAG"])

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
    
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)

@router.post("/ingest")
async def ingest_data(request: IngestRequest):
    """
    Ingest text into Pinecone using local embeddings.
    """
    try:
        # 1. Generate Embeddings locally
        embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")
        vector = embeddings_model.embed_query(request.content)
        
        # 2. Get Pinecone Index
        index = get_pinecone_index()
        
        # 3. Upsert into Pinecone
        import uuid
        index.upsert(vectors=[{
            "id": str(uuid.uuid4()),
            "values": vector,
            "metadata": {"text": request.content}
        }])
        
        return {"status": "success", "message": "Data ingested successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def ask_ai(request: AskRequest):
    """
    Ask a question using Manual RAG (Ollama + Pinecone Direct).
    """
    try:
        # 1. Embed the user query
        embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")
        query_vector = embeddings_model.embed_query(request.query)
        
        # 2. Search Pinecone for context
        index = get_pinecone_index()
        search_results = index.query(vector=query_vector, top_k=3, include_metadata=True)
        
        # 3. Build the context string
        context = "\n".join([res["metadata"]["text"] for res in search_results["matches"] if "text" in res["metadata"]])
        
        if not context:
            context = "No relevant context found in the database."

        # 4. Generate answer using local LLM
        llm = Ollama(model="mistral")
        prompt = f"Use the following context to answer the question.\n\nContext:\n{context}\n\nQuestion: {request.query}\n\nAnswer:"
        
        response = llm.invoke(prompt)
        return {"query": request.query, "answer": response, "context_found": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
