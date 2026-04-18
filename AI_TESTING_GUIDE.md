# 🚀 AI & Pinecone Testing Guide

Use this guide to test how your AI "learns" from the data you save in Pinecone.

---

## 📥 Step 1: Add Knowledge (Ingest)
Copy and paste these commands into your terminal to give the AI some facts about your project.

### Fact 1: Database Setup
```bash
curl -X 'POST' \
  'http://localhost:8000/ai/ingest' \
  -H 'Content-Type: application/json' \
  -d '{"content": "The project uses a PostgreSQL database running on port 5437 via Docker Compose."}'
```

### Fact 2: Authentication
```bash
curl -X 'POST' \
  'http://localhost:8000/ai/ingest' \
  -H 'Content-Type: application/json' \
  -d '{"content": "Users must authenticate using JWT tokens obtained from the /auth/login endpoint."}'
```

### Fact 3: Project Structure
```bash
curl -X 'POST' \
  'http://localhost:8000/ai/ingest' \
  -H 'Content-Type: application/json' \
  -d '{"content": "The backend is built with FastAPI and uses SQLAlchemy as the ORM to communicate with the database."}'
```

---

## ❓ Step 2: Ask Questions (RAG)
Now, ask the AI questions based on the facts above. Even if you don't use the exact words, it will find the answer!

### Question A: About the Database
```bash
curl -X 'POST' \
  'http://localhost:8000/ai/ask' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What port is the database running on?"}'
```

### Question B: About Security
```bash
curl -X 'POST' \
  'http://localhost:8000/ai/ask' \
  -H 'Content-Type: application/json' \
  -d '{"query": "How do users log in and stay authenticated?"}'
```

### Question C: About Technology
```bash
curl -X 'POST' \
  'http://localhost:8000/ai/ask' \
  -H 'Content-Type: application/json' \
  -d '{"query": "What framework and ORM are being used here?"}'
```

---

## 🧠 How to Read the Response
When you call `/ai/ask`, you will get a JSON response:
- **`query`**: Your question.
- **`answer`**: The response from Mistral (Ollama).
- **`context_found`**: The actual text that was retrieved from Pinecone. This is the "proof" that the AI is using your data!

---

## 🛠️ Troubleshooting
- **Error 500?** Make sure you ran `docker-compose up -d` and your virtual environment is active.
- **AI taking too long?** Ensure Ollama is running (`ollama serve`).
