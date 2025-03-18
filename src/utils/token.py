import jwt
import datetime
from typing import Optional
from passlib.context import CryptContext
from src.configs.settings import settings 
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.services.tables import Tables
from src.common.app_constants import AppConstants
from src.common.app_response import AppResponse
from sqlalchemy import select,update
from jose import JWTError
import traceback
from datetime import datetime
import openai

from uuid import UUID
tables = Tables()
app_response = AppResponse()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )



def deduct_tokens_service(user_id: UUID, tokens_to_deduct: int, db: Session):
    """Deduct tokens from the user in the database."""
    
    # Fetch the user token record from the database
    user_token = db.execute(
        select(tables.user_tokens).where(tables.user_tokens.c.user_id == user_id)
    ).fetchone()

    # Check if the user has a token record
    if not user_token:
        raise HTTPException(status_code=404, detail="User tokens not found")

    # You can access the value by index (if you know the column positions)
    # Assuming 'total_tokens' is the 3rd column in the query result, index starts from 0
    total_tokens = user_token[2]  # Index 2 corresponds to the 'total_tokens' column

    # Alternatively, use `user_token['total_tokens']` if the result is a dictionary-like object
    # Check if you can access the column name directly
    # If you're using SQLAlchemy 1.4+ (which provides dict-like behavior), you can do:
    # total_tokens = user_token['total_tokens'] 
    
    # If your result doesn't support this, then stick with accessing by index.

    # Check if the user has enough tokens to deduct
    if total_tokens < tokens_to_deduct:
        raise HTTPException(
            status_code=400,
            detail="Insufficient tokens to complete this request. Please upgrade your plan."
        )

    # Update the tokens in the database
    update_stmt = (
        update(tables.user_tokens)
        .where(tables.user_tokens.c.user_id == user_id)
        .values(total_tokens=total_tokens - tokens_to_deduct, updated_at=datetime.utcnow())
    )
    db.execute(update_stmt)
    db.commit()

    return {"message": "Tokens deducted successfully.", "remaining_tokens": total_tokens - tokens_to_deduct}
