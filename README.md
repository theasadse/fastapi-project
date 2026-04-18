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
