from fastapi import FastAPI, HTTPException
from app.models import ChatRequest, ChatResponse
from app.agent import process_chat

app = FastAPI(title="SHL Conversational Agent")

@app.get("/health")
async def health_check():
    # Required for the evaluator to know your service is awake
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Pass the stateless message array directly to the brain
        response = await process_chat(request.messages)
        return response
    except Exception as e:
        # Prevent the server from crashing if the LLM hiccups
        raise HTTPException(status_code=500, detail=str(e))