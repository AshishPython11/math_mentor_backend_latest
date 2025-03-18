from src.services.chat_ai import chat_with_ai_logic, chat_with_get_logic
from src.schemas.user import  ChatRequest, UpdateChatRequest, DeleteResponse,ConversationResponse,ChatHistoryResponse, RenameConversationRequest,ImageChatSchema
from sqlalchemy.orm import Session
from src.configs.config import get_db
from fastapi import APIRouter, Depends,HTTPException,File, UploadFile,Form
from src.common.app_response import AppResponse
from src.services.tables import Tables
from src.configs.utilites import get_current_user
from sqlalchemy import select , insert , update, delete ,exists
import openai
import os
from src.services.chat_ai import client 
import shutil

from src.common.app_constants import AppConstants
from src.common.messages import Messages
from uuid import UUID, uuid4
from datetime import datetime
import traceback
from src.services.chat_ai import(
get_conversation_messages_service,
rename_conversation_service,
soft_delete_conversation_service,
get_student_conversations_service,
start_or_continue_chat_service,
start_or_continue_chat_service,
process_image_chat_service
)



tables = Tables()
app_response = AppResponse()
router = APIRouter()



@router.post("/chat")
async def process_image_chat(
data: ImageChatSchema = Depends(),
image: UploadFile = None, 
db: Session = Depends(get_db),
current_user: dict = Depends(get_current_user)
):
    """Handles AI chat with image processing"""
    return await process_image_chat_service(data, image, db)



@router.post("/chat/start")
def start_or_continue_chat(request: ChatRequest, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    """Starts a new chat or continues an existing one"""
    return start_or_continue_chat_service(request, db)


@router.put("/conversations/{conversation_id}/rename")
def rename_conversation_title(conversation_id: str, request: RenameConversationRequest, db: Session = Depends(get_db),current_user: dict = Depends(get_current_user)):
    """Renames a conversation title"""
    return rename_conversation_service(conversation_id, request, db)


@router.delete("/conversations/{conversation_id}/delete")
def soft_delete_conversation(conversation_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Soft deletes a conversation"""
    return soft_delete_conversation_service(conversation_id, db)






@router.get("/conversations/student/{student_id}")
def get_student_conversations(student_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Fetches all unique conversations for a given student"""
    return get_student_conversations_service(student_id, db)