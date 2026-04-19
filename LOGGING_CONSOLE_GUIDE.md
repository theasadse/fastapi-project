# Console & Logger Guide (LangChain + RAG + Vector DB)

This document explains **where** logging is added in this project and **why** each log is useful for understanding runtime flow.

## 1) What was added

### Centralized console logger

- File: `app/core/logging.py`
- Purpose: Configure one consistent console format across all modules.
- Format:

```text
YYYY-MM-DD HH:MM:SS | LEVEL | module.path | message
```

### Configurable level from `.env`

- File: `app/core/config.py`
- Setting: `log_level` (env: `LOG_LEVEL`)
- Example in `.env.example`:

```env
LOG_LEVEL=INFO
```

### Startup logging

- File: `app/main.py`
- Why: Shows app lifecycle and DB readiness at startup.

## 2) Where logs are used and why

## `app/main.py`

- `startup.begin`: App boot has started.
- `startup.db_wait.begin` / `startup.db_wait.success`: DB connection check status.
- `startup.db_migrate.begin` / `startup.db_migrate.success`: table creation status.

These logs help you quickly identify whether startup failures are from app init, DB wait, or schema creation.

## `app/routes/chat.py` (LangChain chat flow)

- `chat.model_initialized`: confirms Ollama LLM object is created.
- `chat.cache_backend`: indicates whether cache backend is `redis` or `in-memory`.
- `chat.request_received`: tracks incoming chat requests and message size.
- `chat.memory.loaded`: shows message count and source (`cache` or `database`).
- `chat.memory.loaded ... long_term_memory=True/False`: shows whether long-term memory was also loaded.
- `chat.llm_invoke.begin`: marks start of model inference.
- `chat.memory.saved`: confirms user+assistant messages were persisted to session memory.
- `chat.llm_invoke.success`: shows latency and output size.
- `chat.cache.flush_triggered`: cache write-behind batch flushed to DB.

Additional long-term memory logs:

- `chat.long_term_memory.saved`: long-term memory updated for session.
- `chat.long_term_memory.cleared`: long-term memory removed for session.

Additional semantic memory logs:

- `chat.semantic_memory.search_failed`: Pinecone retrieval issue during chat.
- `chat.semantic_memory.saved`: automatic save of important user message.
- `chat.semantic_memory.save_failed`: automatic semantic save failed.
- `chat.semantic_memory.manual_saved`: manual semantic memory save endpoint called.

Cache flush lifecycle logs:

- `shutdown.chat_cache_flush.begin`: pending cache writes at app shutdown.
- `shutdown.chat_cache_flush.success`: total writes flushed to DB at shutdown.

These logs help measure inference time and verify memory is loaded and saved for follow-up questions.

### Chat memory endpoints

- `POST /chat/` with `session_id` reuses memory.
- `GET /chat/history/{session_id}` returns full stored memory.
- `DELETE /chat/history/{session_id}` clears stored memory.
- `PUT /chat/memory/{session_id}` saves long-term memory for that session.
- `GET /chat/memory/{session_id}` reads long-term memory.
- `DELETE /chat/memory/{session_id}` clears long-term memory.
- `PUT /chat/memory/semantic/{session_id}` embeds and stores semantic memory in Pinecone.
- `POST /chat/memory/semantic/{session_id}/search` retrieves relevant semantic memories.

## `app/routes/ai.py` (RAG flow)

### `/ai/ingest`

- `rag.ingest.request_received`: new ingest request received.
- `rag.ingest.embedding.begin` / `success`: local embedding generation with dimensions.
- `rag.ingest.vector_db_connect.begin` / `success`: Pinecone connection health.
- `rag.ingest.upsert.begin`: vector upsert operation started.
- `rag.ingest.completed`: total ingest latency.
- `rag.ingest.failed`: full exception stack if ingest fails.

### `/ai/ask`

- `rag.ask.request_received`: incoming user query.
- `rag.ask.embedding.begin` / `success`: query embedding generated.
- `rag.ask.retrieve.begin` / `success`: Pinecone retrieval and match count.
- `rag.ask.retrieve.failed` / `skipped`: fallback path (e.g., no key or retrieval error).
- `rag.ask.context_built`: whether RAG context was actually used.
- `rag.ask.generation.begin`: LLM generation started.
- `rag.ask.completed`: total latency and answer size.
- `rag.ask.failed`: full exception stack if query handling fails.

These logs let you debug the **exact RAG stages**: embed → retrieve → context build → generate.

## 3) How to run and watch console logs

Run the app:

```bash
cd /Users/hello/Desktop/AI-Projects/fastapi-project
source .venv/bin/activate
uvicorn app.main:app --reload
```

In another terminal, trigger a RAG query:

```bash
curl -X POST http://127.0.0.1:8000/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What framework does this project use?"}'
```

You should see logs in order:

1. `rag.ask.request_received`
2. `rag.ask.embedding.*`
3. `rag.ask.retrieve.*`
4. `rag.ask.context_built`
5. `rag.ask.generation.begin`
6. `rag.ask.completed`

## 4) Recommended log levels

- `INFO` (default): Best for understanding normal flow.
- `DEBUG`: Adds lower-level messages (e.g., Pinecone connect debug line).
- `WARNING`/`ERROR`: Focus only on issues.

Set level in `.env`:

```env
LOG_LEVEL=DEBUG
```

## 5) Why this helps learning RAG

With these logs, you can answer:

- Did embedding generation run?
- Was Pinecone queried successfully?
- Did we get matches or fallback?
- Was context used in the final prompt?
- How long each request took?

That gives you a practical, observable understanding of how LangChain + Ollama + Pinecone are working in your project.

## 6) How embeddings are created from prompt text

In this project, embeddings are created in two places:

- Ingest flow: `app/routes/ai.py` → `ingest_data()`
- Ask flow: `app/routes/ai.py` → `ask_ai()`

Both use:

```python
embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")
vector = embeddings_model.embed_query(text)
```

### What happens internally (conceptual)

1. You send text (`content` in ingest or `query` in ask).
2. The embedding model tokenizes and encodes semantic meaning.
3. It outputs a dense numeric vector (here typically 1024 dimensions).
4. That vector is used for:

- **Upsert** to Pinecone (`/ai/ingest`)
- **Similarity search** in Pinecone (`/ai/ask`)

Think of embeddings as coordinates in semantic space:

- Similar meaning texts → vectors close together
- Different meaning texts → vectors far apart

### New DEBUG logs that show this conversion

Set:

```env
LOG_LEVEL=DEBUG
```

Then you will see logs like:

- `rag.ingest.embedding.input`: sanitized prompt preview + char/word counts
- `rag.ingest.embedding.success`: vector dimension count
- `rag.ingest.embedding.vector_sample`: first few float values from the vector
- `rag.ask.embedding.input`: query preview + char/word counts
- `rag.ask.embedding.success`: query vector dimension count
- `rag.ask.embedding.vector_sample`: first few float values from query vector

Example (shape):

```text
... | DEBUG | app.routes.ai | rag.ask.embedding.input request_id=abcd1234 query_preview='What framework is this backend using?' chars=39 words=6
... | INFO  | app.routes.ai | rag.ask.embedding.success request_id=abcd1234 vector_dimensions=1024
... | DEBUG | app.routes.ai | rag.ask.embedding.vector_sample request_id=abcd1234 sample=[0.012941, -0.031102, 0.004882, 0.077331, -0.009412]
```

This is the exact point where your prompt text becomes a machine-searchable vector.
