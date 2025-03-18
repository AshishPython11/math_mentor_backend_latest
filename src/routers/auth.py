from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer,HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.configs.config import get_db
from src.services.auth_service import (
    signup_service,
    login_service,
    forgot_password_service,
    reset_password_service,
    change_password_service,
)
from src.schemas.user import UserSignup, ForgotPassword, ResetPassword, ChangePassword , ChatRequest
from src.configs.utilites import get_current_user
from fastapi import BackgroundTasks
from src.common.app_response import AppResponse
from src.common.app_constants import AppConstants
from src.common.messages import Messages
from fastapi.security import OAuth2PasswordBearer


router = APIRouter()
token_auth_scheme = HTTPBearer()
app_response = AppResponse()


# @router.get("/protected")
# def protected_route(credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme)):
#     token = credentials.credentials  # Extract the token
#     user = get_current_user(token)  # Decode and verify the token
#     if not user:
#         return {"error": "Invalid token"}
#     return {"message": "You are authorized", "user": user}

@router.post("/signup")
async def signup(user: UserSignup, db: Session = Depends(get_db)):
    app_response = signup_service(user, db)
    return app_response

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    app_response =login_service(form_data, db)
    return app_response

@router.post("/forgot-password")
async def forgot_password(background_tasks: BackgroundTasks , request: ForgotPassword, db: Session = Depends(get_db)):
    app_response = await forgot_password_service(request, db, background_tasks)
    return app_response

@router.post("/reset-password")
async def reset_password(request: ResetPassword, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    app_response = reset_password_service(request, db)
    return app_response



@router.post("/change-password")    
def change_password(request: ChangePassword, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Changes the user's password"""
    return change_password_service(request, db)



