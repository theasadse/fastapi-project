import os
from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Pinecone as PineconeVectorStore
from langchain_text_splitters import CharacterTextSplitter
from langchain_classic.chains import RetrievalQA
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

# Load environment variables from .env
load_dotenv()

def setup_pinecone_index(index_name):
    """
    Ensures the Pinecone index exists.
    """
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Check if index exists, if not create it
    existing_indexes = [index.name for index in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating Pinecone index: {index_name}...")
        pc.create_index(
            name=index_name,
            dimension=1024, # Matches user's Pinecone index
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
    return pc.Index(index_name)

def main():
    print("--- Pinecone & LangChain RAG Demo (LOCAL MODELS) ---")
    
    # 1. Configuration
    index_name = os.getenv("PINECONE_INDEX_NAME", "fastapi-docs")
    
    # Check for Pinecone API key
    if not os.getenv("PINECONE_API_KEY"):
        print("ERROR: Please set PINECONE_API_KEY in your .env file.")
        print("Pinecone is free to sign up at https://pinecone.io")
        return

    # 2. Define Local Embeddings Model (using Ollama)
    # This model produces 1024-dimension vectors
    print("Loading local embeddings (mxbai-embed-large)...")
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")

    # 3. Sample Data (The Knowledge Base)
    raw_documents = [
        "The project uses FastAPI as the web framework and SQLAlchemy for ORM.",
        "The database is PostgreSQL, running on port 5437 via Docker.",
        "Authentication is handled via JWT tokens in the /auth endpoint.",
        "Deployment is managed using Docker Compose for local development."
    ]
    
    # Convert strings to Document objects
    docs = [Document(page_content=t) for t in raw_documents]

    # 4. Connect to Pinecone and Upsert Data
    setup_pinecone_index(index_name)
    
    print("\nIndexing documents into Pinecone...")
    vectorstore = PineconeVectorStore.from_documents(
        docs, 
        embeddings, 
        index_name=index_name
    )
    print("Indexing complete!")

    # 5. Retrieval Augmented Generation (RAG)
    # Using local LLM via Ollama (e.g., Mistral or Llama3)
    # Make sure you have run: ollama pull mistral
    print("Connecting to local LLM (mistral)...")
    llm = Ollama(model="mistral")
    
    # Create the RAG chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever()
    )

    # 6. Ask a Question
    query = "How is the database managed in this project?"
    print(f"\nUser Query: {query}")
    
    try:
        response = qa_chain.invoke(query)
        print("\n--- AI Response (using Local RAG) ---")
        print(response["result"])
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Make sure Ollama is running and you have pulled the models: 'nomic-embed-text' and 'mistral'.")

    print("\n--- How it worked? ---")
    print("1. Local Embedding: Ollama turned your query into numbers locally.")
    print("2. Pinecone: The cloud vector DB found the matches.")
    print("3. Local LLM: Ollama processed the found data and generated the final answer.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
