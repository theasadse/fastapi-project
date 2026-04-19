# FastAPI Project

FastAPI project with PostgreSQL, SQLAlchemy ORM, and pgAdmin.

## Run locally

1. Copy `.env.example` to `.env`.
2. Start infrastructure with `docker compose up -d`.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run the app with `uvicorn app.main:app --reload`.

## Services

- API: `http://127.0.0.1:8000`
- pgAdmin: `http://127.0.0.1:5050`
- PostgreSQL: `localhost:5437`
- Redis: `localhost:6382`
- RedisInsight: `http://127.0.0.1:5540`

## Chat Memory (Session-Based)

The `/chat/` endpoint now supports persistent memory per `session_id`.

- Send `session_id` in request body to continue the same conversation.
- If `session_id` is not provided, the API creates one and returns it.
- Previous messages from the same session are included in prompt context.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/chat/ \
	-H "Content-Type: application/json" \
	-d '{"session_id":"asad-session","message":"My name is Asad"}'
```

Follow-up request with same memory:

```bash
curl -X POST http://127.0.0.1:8000/chat/ \
	-H "Content-Type: application/json" \
	-d '{"session_id":"asad-session","message":"What is my name?"}'
```

Read stored history:

```bash
curl http://127.0.0.1:8000/chat/history/asad-session
```

Clear stored history:

```bash
curl -X DELETE http://127.0.0.1:8000/chat/history/asad-session
```

## Long-Term Memory (Independent of Chat History)

Use long-term memory when you want the assistant to remember stable facts (for example: name, preferences), even after clearing chat history.

- `DELETE /chat/history/{session_id}` removes only conversation turns.
- Long-term memory stays until you delete it with `DELETE /chat/memory/{session_id}`.

Save/update long-term memory:

```bash
curl -X PUT http://127.0.0.1:8000/chat/memory/asad-session \
	-H "Content-Type: application/json" \
	-d '{"memory":"User name is Asad. Preferred language is English."}'
```

Read long-term memory:

```bash
curl http://127.0.0.1:8000/chat/memory/asad-session
```

Delete long-term memory:

```bash
curl -X DELETE http://127.0.0.1:8000/chat/memory/asad-session
```

## Semantic Memory (Pinecone / RAG-style)

The chatbot now also supports semantic memory in Pinecone.

- Only important messages are auto-stored (not every chat line).
- Query-time retrieval fetches relevant semantic memories and adds them to prompt context.
- Semantic memory is namespaced by `session_id`.

Manually store semantic memory:

```bash
curl -X PUT http://127.0.0.1:8000/chat/memory/semantic/asad-session \
	-H "Content-Type: application/json" \
	-d '{"memory":"Asad is building a software company."}'
```

Search semantic memory:

```bash
curl -X POST http://127.0.0.1:8000/chat/memory/semantic/asad-session/search \
	-H "Content-Type: application/json" \
	-d '{"query":"What is Asad building?", "top_k": 3}'
```

`POST /chat/` response includes:

- `memory_messages_used`: short-term conversation messages used
- `long_term_memory_used`: whether DB long-term memory was used
- `semantic_memories_used`: number of Pinecone memories injected

## Chat Caching Layer (Write-Behind)

Chat now uses a bounded in-memory cache for short-term conversation context, then flushes to PostgreSQL in batches.

- Fast path: `/chat/` reads recent messages from cache.
- Miss path: if cache is empty for a session, recent messages are loaded from DB and cache is warmed.
- Write-behind: new user/assistant messages are first appended to cache, then persisted in DB when pending writes reach `CHAT_CACHE_FLUSH_BATCH_SIZE`.
- Consistency: `/chat/history/{session_id}` flushes pending writes for that session before reading.
- Safety: app shutdown flushes any remaining pending writes.

Environment knobs:

- `REDIS_URL` (example: `redis://localhost:6382/0`)
- `CHAT_CACHE_KEY_PREFIX` (default `chat-cache`)
- `CHAT_CACHE_SESSION_MESSAGE_LIMIT` (default `20`)
- `CHAT_CACHE_MAX_SESSIONS` (default `2000`)
- `CHAT_CACHE_SESSION_TTL_SECONDS` (default `86400`)
- `CHAT_CACHE_FLUSH_BATCH_SIZE` (default `100`)

### Redis setup

Start Redis with Docker Compose:

```bash
docker compose up -d redis
```

### RedisInsight GUI setup

Start RedisInsight:

```bash
docker compose up -d redisinsight
```

Open:

```text
http://127.0.0.1:5540
```

In RedisInsight, add database with:

- Host: `redis`
- Port: `6379`
- Username: _(leave empty)_
- Password: _(leave empty unless you configure Redis auth)_

If connecting from your host network instead, use:

- Host: `127.0.0.1`
- Port: `6382`

If `REDIS_URL` is set and reachable, chat cache backend uses Redis.
If Redis is not reachable, it safely falls back to in-memory cache.
