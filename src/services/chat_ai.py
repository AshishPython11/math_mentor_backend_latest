from fastapi import UploadFile
from sqlalchemy.orm import Session
from io import BytesIO
from PIL import Image
from src.utils.token import deduct_tokens_service
from src.schemas.user import ImageChatSchema
from src.common.app_constants import AppConstants
from src.common.messages import Messages
from src.common.app_response import AppResponse
import requests
from src.services.tables import Tables
from datetime import datetime
from sqlalchemy import select, update, insert
import openai
import os
import base64
from uuid import UUID, uuid4
import uuid
from fastapi.encoders import jsonable_encoder

def is_valid_uuid(value: str) -> bool:
    """Checks if the given string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
    


tables = Tables()
app_response = AppResponse()
api_key = os.getenv("OPENAI_API_KEY")



if not api_key:
    raise ValueError("API key not found. Set OPENAI_API_KEY environment variable.")

client = openai.OpenAI(api_key=api_key) 
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

def query_gpt4_turbo(prompt):
    """Send the prompt to GPT-4 Turbo and return the response."""
    try:
        response = client.chat.completions.create(  # Corrected method for OpenAI v1.0+
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Adjust randomness
            max_tokens=100,  # Adjust max length
            top_p=0.9,  # Nucleus sampling
            frequency_penalty=0.0,  # Control word repetition
            presence_penalty=0.0  # Encourage new topic discussion
        )

        return response.choices[0].message.content  # Correct way to get response
    except openai.OpenAIError as e:
        return f"OpenAI API Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

# Example usage
prompt = "Explain Newton's third law of motion."
response = query_gpt4_turbo(prompt)


def chat_with_ai_logic(data, db: Session):
    """Function to handle user input, AI response, and store the data in the database."""
    user_id = data.user_id
    user_prompt = data.prompt

    # Check if user exists
    user = db.execute(select(tables.users).where(tables.users.c.id == user_id)).fetchone()
    if not user:
        return jsonable_encoder({
            "code": AppConstants.CODE_INVALID_REQUEST,
            "message": Messages.NOT_FOUND_USER_DETAILS,
            "success": False
        })

    # Check for available tokens
    user_tokens = db.query(tables.user_tokens).filter(tables.user_tokens.c.user_id == user_id).first()
    if not user_tokens or user_tokens.total_tokens <= 0:
        app_response.set_response(AppConstants.CODE_INSUFFICIENT_TOKENS, {}, Messages.INSUFFICIENT_TOKENS, False)
        return app_response

    # Deduct 1 token for this interaction
    deduct_tokens_service(user_id, 1, db)

    # Get AI response using GPT-4 Turbo
    ai_response = query_gpt4_turbo(user_prompt)

    if not ai_response:
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.ERROR_GENERATING_AI_RESPONSE, False)
        return app_response

    # Store the query and response in the database
    insert_stmt = tables.user_queries.insert().values(
        user_id=user_id,
        question=user_prompt,
        answer=ai_response,
        tokens_used=1,
        created_at=datetime.utcnow()
    )
    db.execute(insert_stmt)
    db.commit()

    # Return AI response and remaining tokens
    remaining_tokens = user_tokens.total_tokens - 1
    return {"ai_response": ai_response, "remaining_tokens": remaining_tokens}

# In your signup or initial token allocation function:
def add_tokens_to_user(user_id: UUID, tokens_purchased: int, db: Session):
    """Function to add tokens to a user after a successful payment or signup."""
    user_token = db.query(tables.user_tokens).filter(tables.user_tokens.c.user_id == user_id).first()
    
    if user_token:
        user_token.total_tokens += tokens_purchased
        user_token.updated_at = datetime.utcnow()
    else:
        # If no token record exists, create one
        new_user_token = tables.user_tokens.insert().values(
            user_id=user_id,
            total_tokens=tokens_purchased,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.execute(new_user_token)
    
    db.commit()




def chat_with_get_logic(db: Session):
    # Query all questions and answers from user_queries table
    query = select(tables.user_queries.c.question, tables.user_queries.c.answer)
    result = db.execute(query).fetchall()  # Fetch all records

    # Convert the result to a list of dictionaries
    qa_pairs = [{"question": row[0], "answer": row[1]} for row in result]

    return {"data": qa_pairs}







def get_conversation_messages_service(conversation_id: str, db: Session):
    """Fetch conversation details and chat history"""

    if not is_valid_uuid(conversation_id):
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.INVALID_CONVERSATION_ID, False)
        return app_response

    # ✅ First, check if conversation exists
    conversation = db.execute(
        select(tables.conversations.c.id, tables.conversations.c.title)
        .where(tables.conversations.c.id == conversation_id)
    ).mappings().first()

    if not conversation:
        app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, "Conversation not found", False)
        return app_response

    # ✅ Fetch chat messages
    chats = db.execute(
        select(
            tables.chat_history.c.conversation_id,
            tables.chat_history.c.prompt,
            tables.chat_history.c.ai_response,
            tables.chat_history.c.created_at
        )
        .where(tables.chat_history.c.conversation_id == conversation_id)
    ).mappings().all()

    # ✅ Format the response
    conversation_data = {
        "conversation_id": conversation_id,
        "title": conversation["title"],
        "messages": chats  # Empty list if no messages
    }

    app_response.set_response(AppConstants.CODE_SUCCESS, conversation_data, Messages.MESSAGES_FETCHED, True)
    return app_response



def rename_conversation_service(conversation_id: str, request, db: Session):
    """Renames a conversation title if it exists"""
    
    if not is_valid_uuid(conversation_id):
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.INVALID_CONVERSATION_ID, False)
        return app_response

    # ✅ Check if the conversation exists
    chat_exists = db.execute(
        select(tables.conversations.c.id).where(tables.conversations.c.id == conversation_id)
    ).scalar()

    if not chat_exists:
        app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.CONVERSATION_NOT_FOUND, False)
        return app_response

    # ✅ Update the conversation title
    db.execute(
        update(tables.conversations)
        .where(tables.conversations.c.id == conversation_id)
        .values(title=request.new_title)
    )
    db.commit()

    # ✅ Fetch the updated title
    updated_conversation = db.execute(
        select(tables.conversations.c.title)
        .where(tables.conversations.c.id == conversation_id)
    ).scalar()

    app_response.set_response(AppConstants.CODE_SUCCESS, {
        "conversation_id": conversation_id,
        "new_title": updated_conversation
    }, Messages.CONVERSATION_RENAMED, True)
    return app_response


def get_student_conversations_service(student_id: str, db: Session):
    """Fetches all unique conversations for a given student"""

    conversations = db.execute(
        select(tables.chat_history.c.conversation_id, tables.chat_history.c.subject_id)
        .distinct()
        .where(tables.chat_history.c.user_id == student_id)
    ).fetchall()

    if not conversations:
        app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.NO_CONVERSATIONS_FOUND, False)
        return app_response

    app_response.set_response(AppConstants.CODE_SUCCESS, [
        {"conversation_id": conv.conversation_id, "subject_id": conv.subject_id} for conv in conversations
    ], Messages.CONVERSATIONS_FETCHED, True)
    return app_response




def soft_delete_conversation_service(conversation_id: str, db: Session):
    """Soft deletes a conversation and its associated chat history"""

    if not is_valid_uuid(conversation_id):
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.INVALID_CONVERSATION_ID, False)
        return app_response

    # ✅ Check if the conversation exists and is not already deleted
    conversation_exists = db.execute(
        select(tables.conversations.c.id).where(
            tables.conversations.c.id == conversation_id, 
            tables.conversations.c.is_deleted == False
        )
    ).scalar()

    if not conversation_exists:
        app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.CONVERSATION_NOT_FOUND, False)
        return app_response

    # ✅ Soft delete all messages in chat history
    db.execute(update(tables.chat_history)
        .where(tables.chat_history.c.conversation_id == conversation_id)
        .values(is_deleted=True, is_active=False)  # Set is_active=False
    )

    # ✅ Soft delete the conversation
    db.execute(update(tables.conversations)
        .where(tables.conversations.c.id == conversation_id)
        .values(is_deleted=True, is_active=False)  # Set is_active=False
    )

    db.commit()

    app_response.set_response(AppConstants.CODE_SUCCESS, {}, Messages.CONVERSATION_DELETED, True)
    return app_response


UPLOAD_FOLDER = "uploads" 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


async def process_image_chat_service(data: ImageChatSchema, image: UploadFile, db: Session):
    """Handles AI chat with image processing & stores image in DB"""
    try:
        user_id = data.user_id
        prompt = data.prompt

        messages = [{"role": "user", "content": prompt}]

        # ✅ Get latest chat_history entry for user
        chat_history_entry = db.execute(
            select(tables.chat_history.c.id)
            .where(tables.chat_history.c.user_id == user_id)
            .order_by(tables.chat_history.c.created_at.desc())
        ).fetchone()

        if chat_history_entry:
            chat_id = chat_history_entry[0]
        else:
            # ✅ Create new chat history if none exists
            chat_history_insert = db.execute(
                insert(tables.chat_history)
                .values(
                    user_id=user_id,
                    conversation_id=str(uuid4()),  # New conversation
                    prompt=prompt,
                    ai_response="{}",
                    tokens_used=0,
                    created_at=datetime.now(),
                    is_deleted=False
                )
                .returning(tables.chat_history.c.id)
            )
            chat_id = chat_history_insert.fetchone()[0]
            db.commit()

        # ✅ If an image is uploaded, save it in `uploads/`
        if image:
            file_extension = image.filename.split(".")[-1]
            image_filename = f"{uuid4()}.{file_extension}"
            file_path = os.path.join(UPLOAD_FOLDER, image_filename)

            with open(file_path, "wb") as buffer:
                buffer.write(await image.read())  # ✅ `await` is needed for async read

            image_url = f"/uploads/{image_filename}"
            file_url = f"uploads/{image_filename}"

            # ✅ Store Image URL in `media_uploads`
            db.execute(
                insert(tables.media_uploads).values(
                    user_id=user_id,
                    chat_history_id=chat_id,  # ✅ Ensure `chat_id` is set correctly
                    media_type="image",
                    file_url=file_url,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            )
            db.commit()

            # ✅ Convert image to Base64 for OpenAI
            with open(file_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")

            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            })

        # ✅ Send request to OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages
        )

        response_data = {
            "prompt": prompt,
            "ai_response": response.choices[0].message.content,
            "image_filename": image_filename if image else None,
            "image_url": image_url if image else None
        }

        app_response.set_response(AppConstants.CODE_SUCCESS, response_data, Messages.CHAT_SAVED, True)
        return app_response

    except Exception as e:
        # ✅ Improved error handling for better debugging
        print(f"Error in process_image_chat_service: {e}")
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR, {}, f"Error: {str(e)}", False)
        return app_response



def start_or_continue_chat_service(request, db: Session):
    """Handles starting a new chat or continuing an existing one"""
    try:
        print(f"🚀 Chat API Called - Request Data: {request.dict()}")

        # ✅ Check if user has available tokens before performing any database operations
        print(f"Checking tokens for user {request.user_id}...")
        user_tokens = db.query(tables.user_tokens).filter(tables.user_tokens.c.user_id == request.user_id).first()

        if not user_tokens or user_tokens.total_tokens <= 0:
            print(f"❌ Insufficient tokens for user {request.user_id}. Tokens remaining: {user_tokens.total_tokens if user_tokens else 0}")
            # Return early with insufficient tokens response and stop execution
            app_response.set_response(AppConstants.CODE_INSUFFICIENT_TOKENS, {}, "Insufficient tokens. Please purchase more.", False)
            return app_response

        print(f"✅ User {request.user_id} has {user_tokens.total_tokens} tokens available.")

        # ✅ Generate a new conversation_id if not provided
        if request.conversation_id in [None, "", "string"]:
            conversation_id = str(uuid4())  # Generate new UUID
        else:
            conversation_id = request.conversation_id

        # ✅ Generate a default title based on the first prompt
        default_title = request.prompt[:30] + "..." if request.prompt else "New Chat"

        # ✅ Ensure subject_id exists in the request, default to 5 if not provided or if it is 0
        subject_id = request.subject_id if request.subject_id not in [None, 0] else 5

        # ✅ Check if subject_id exists in the subjects table
        subject_exists = db.execute(
            select(tables.subjects.c.id).where(tables.subjects.c.id == subject_id)
        ).scalar()

        # If the subject does not exist, raise an error
        if not subject_exists:
            raise ValueError(f"Subject ID {subject_id} not found in subjects table")

        # ✅ Check if conversation exists
        existing_conversation = db.execute(
            select(tables.conversations.c.id).where(
                tables.conversations.c.id == conversation_id,
                tables.conversations.c.user_id == request.user_id
            )
        ).scalar()

        # If conversation doesn't exist, create a new one
        if not existing_conversation:
            print(f"🆕 Creating new conversation: {conversation_id} with title: {default_title}")
            db.execute(
                insert(tables.conversations).values(
                    id=conversation_id,
                    user_id=request.user_id,
                    subject_id=subject_id,  # Use the correct subject_id
                    title=default_title,
                    created_at=datetime.now()
                )
            )
            db.commit()

        # ✅ Call AI function for response (Only if there are sufficient tokens)
        ai_result = chat_with_ai_logic(request, db)
        if not ai_result:
            print(f"❌ Error generating AI response.")
            app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.ERROR_GENERATING_AI_RESPONSE, False)
            return app_response
        
        ai_response = ai_result["ai_response"]
        remaining_tokens = ai_result["remaining_tokens"]

        # ✅ Insert chat history with subject_id (Only after AI response)
        chat_id = db.execute(
            insert(tables.chat_history).values(
                user_id=request.user_id,
                conversation_id=conversation_id,
                subject_id=subject_id,  # Correctly insert subject_id here
                prompt=request.prompt,
                ai_response=ai_response,
                tokens_used=1,
                created_at=datetime.now()
            ).returning(tables.chat_history.c.id)
        ).scalar()
        db.commit()

        print(f"✅ Chat Saved with ID: {chat_id}")

        # Response data
        response_data = {
            "conversation_id": conversation_id,
            "chat_id": chat_id,
            "subject_id": subject_id,
            "title": default_title,
            "ai_response": ai_response,
            "remaining_tokens": remaining_tokens
        }

        app_response.set_response(AppConstants.CODE_SUCCESS, response_data, Messages.CHAT_SAVED, True)
        return app_response

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR, {}, str(e), False)
        return app_response

