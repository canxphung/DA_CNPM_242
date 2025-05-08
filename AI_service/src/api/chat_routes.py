# src/api/chat_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.core.greenhouse_ai_service import GreenhouseAIService
from src.api.app import get_service

router = APIRouter()

class ChatMessage(BaseModel):
    """Model for chat message request."""
    text: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Model for chat message response."""
    text: str
    intent: str
    actions_taken: List[str]
    timestamp: str

@router.post("/message", response_model=ChatResponse)
async def process_message(
    message: ChatMessage,
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Process a chat message from the user.
    
    This endpoint accepts a message from the user and processes it
    to determine intent, extract entities, and formulate a response.
    It also triggers any necessary actions based on the intent.
    """
    if not message.text:
        raise HTTPException(status_code=400, detail="Message text cannot be empty")
    
    result = service.process_user_message(
        message_text=message.text,
        user_id=message.user_id
    )
    
    return {
        "text": result["response"],
        "intent": result["intent"],
        "actions_taken": result["actions_taken"],
        "timestamp": result["timestamp"]
    }