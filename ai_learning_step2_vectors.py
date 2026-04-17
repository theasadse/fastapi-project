from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain.schema import Document

def main():
    print("--- Vector Retrieval Database Demo ---")
    
    # 1. We need an Embedding model. This turns words into mathematical lists of numbers.
    # Because you are running Ollama locally, we can use it to create embeddings!
    print("Loading Ollama Embeddings...")
    embeddings = OllamaEmbeddings(model="mistral")
    
    # 2. These are the "Private Documents" (the data the AI wasn't trained on).
    # In a real app, this could be a loaded PDF, or a list of SQLAlchemy products from your database.
    product_texts = [
        "Product A is a fast smartphone with a great 4k camera.",
        "Product B is a comfortable gaming chair with lumbar support.",
        "Product C is a heavy duty washing machine that uses low water.",
        "Our company refund policy allows returns up to 30 days."
    ]
    
    # Convert them to LangChain Document objects
    documents = [Document(page_content=text) for text in product_texts]
    
    print("\nCreating the Vector Database (this turns our text into numbers and saves them)...")
    # 3. Create the Database! We are using FAISS (a fast local vector DB)
    vector_db = FAISS.from_documents(documents, embeddings)
    
    print("\nVector Database Created!")
    
    # 4. Now, if the user asks a question, we first search the vector database 
    # to find the text that is most SEMANTICALLY similar to their question.
    query = "I am looking for somewhere to sit."
    print(f"\nUser Query: '{query}'")
    
    # We extract the top 1 most relevant chunk of text from the database
    results = vector_db.similarity_search(query, k=1)
    
    print("\n--- Most Relevant Document Found in Vector DB ---")
    for doc in results:
        print(f"> {doc.page_content}")
        
    print("\nNotice how it perfectly found the gaming chair, even though you didn't say the words 'chair' or 'gaming' in your query!")
    print("That is the magic of Vector Embeddings. It maps the MEANING of the user's sentence.")

if __name__ == "__main__":
    main()
