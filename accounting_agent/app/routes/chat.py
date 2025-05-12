from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import json
import uuid
from typing import List, Optional
from app.services.chat_service import chat_stream
import traceback
from app.services.process_docs import process_documents

router = APIRouter()

@router.post("/chat")
async def chat(
    message: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    conversation_id: Optional[str] = Form(None),
):
    try:
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        sys_messages = []
        if files:
            sys_messages = await process_documents(files, conversation_id)
        
        return StreamingResponse(
            chat_stream(message, conversation_id, sys_messages), 
            media_type="application/json"
        )

    except Exception as e:
        print(f"Error in /chat endpoint: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Chat service error: {e}")