from langchain_community.llms import Ollama

def main():
    print("Connecting to Mistral via Ollama...")
    # Initialize the LLM. 
    # Make sure you have Ollama running and the mistral model pulled!
    llm = Ollama(model="mistral")

    # This is our raw string prompt
    prompt = "Explain in one sentence why learning AI Engineering with LangChain is a good idea."
    
    print(f"User Prompt: {prompt}\n")
    print("Waiting for AI response...\n")
    
    # Send the prompt to the model and retrieve the text response
    response = llm.invoke(prompt)
    
    print("AI Response:")
    print(response)

if __name__ == "__main__":
    main()
