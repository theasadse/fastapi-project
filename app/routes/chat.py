from fastapi import APIRouter
from langchain_community.llms import Ollama

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

# Initialize the LLM here so it's loaded once and ready for requests
llm = Ollama(model="mistral")

@router.post("/", response_model=ChatResponse)
def chat_with_ai(payload: ChatRequest):
    """
    Receives a message from the frontend, sends it to Mistral via LangChain, and returns the response.
    """
    # Simply invoke the model with the user's string message
    ai_response = llm.invoke(payload.message)
    
    # Return the AI's response to the frontend client
    return ChatResponse(reply=ai_response)
