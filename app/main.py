from fastapi import FastAPI, HTTPException
from app.models import ChatRequest, ChatResponse
from app.agent import process_chat

app = FastAPI(title="SHL Conversational Agent")

@app.get("/health")
async def health_check():
    # Required for the evaluator to know your service is awake
    return {"status": "ok"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        return await process_chat(request.messages)
    except Exception as e:
        print(f"ERROR IN CHAT: {e}") # This will show up in Render logs
        raise e