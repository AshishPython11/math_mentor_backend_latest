from pydantic import BaseModel, EmailStr, Field, validator, HttpUrl
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, UUID4

class UserSignup(BaseModel):
    name: str 
    email: EmailStr 
    password: str 
    confirm_password: str 
    grade: int
    birth_date: date = Field(..., description="Date of birth (DD-MM-YYYY)")



    # Validator to ensure password and confirm_password match
    @validator('confirm_password')
    def check_passwords_match(cls, v, values):
        if 'password' in values and values['password'] != v:
            raise ValueError('Passwords do not match')
        return v
    
    @validator("birth_date", pre=True)
    def parse_birth_date(cls, value):
        """Convert DD-MM-YYYY string to date object."""
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%d-%m-%Y").date()
            except ValueError:
                raise ValueError("Invalid date format. Use DD-MM-YYYY.")
        return value
    

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern="^\d{6}$") 
    new_password: str 

class ChangePassword(BaseModel):
    email: EmailStr
    current_password: str
    new_password: str
    confirm_password: str
# Chat request model

class ChatRequest(BaseModel):
    user_id: str
    prompt: str
    subject_id:int
    conversation_id: Optional[str] = None 


class ChatHistoryResponse(BaseModel):
    chat_id: int
    conversation_id: str
    user_id: str
    subject_id: int
    prompt: str
    ai_response: str
    tokens_used: int
    created_at: datetime
    


class ConversationResponse(BaseModel):
    conversation_id: str
    user_id: str
    created_at: datetime

class UpdateChatRequest(BaseModel):
    chat_id: int
    new_response: str

class DeleteResponse(BaseModel):
    message: str
class RenameConversationRequest(BaseModel):
    new_title: str


class ImageChatSchema(BaseModel):
    user_id: UUID
    prompt: str

 
 

    model_config = {  
        "arbitrary_types_allowed": True  # ✅ Fix for datetime
    }


    model_config = {  
        "arbitrary_types_allowed": True,  # ✅ Allows datetime, UUID, etc.
        "str_strip_whitespace": True,  
        "str_min_length": 3  
    } 