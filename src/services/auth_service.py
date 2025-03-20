from datetime import timedelta, datetime
from fastapi import HTTPException , BackgroundTasks
from sqlalchemy.orm import Session
from src.services.tables import Tables
from src.configs.utilites import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp,
    send_email,
)
from src.common.app_response import AppResponse
from sqlalchemy import select
from src.common.app_constants import AppConstants
from src.common.messages import Messages
from sqlalchemy.exc import IntegrityError
# In your auth_service.py (or any other file)
from src.configs.settings import settings 

app_response = AppResponse()
tables = Tables()


def signup_service(user, db: Session):
    try:
        # Check if required fields are present
        if not user.name or not user.email or not user.password:
            app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.VALIDATE_DATA, False)
            return app_response

        # Check if the user already exists
        existing_user = db.execute(select(tables.users).where(tables.users.c.email == user.email)).fetchone()
        if existing_user:
            app_response.set_response(AppConstants.USER_ALREADY_EXISTS, {}, Messages.USER_ALREADY_EXISTS, False)
            return app_response

        # Hash the user's password
        hashed_password = hash_password(user.password)

        # Insert the user into the 'users' table
        insert_user_stmt = tables.users.insert().values(
            name=user.name,
            email=user.email,
            password=hashed_password,
            grade=user.grade,
            birth_date = user.birth_date,
            is_paid=False,  # Assuming user starts with a free plan
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Execute the user insertion query
        result = db.execute(insert_user_stmt)
        db.commit()

        # Get the newly created user's ID
        new_user_id = result.inserted_primary_key[0]

        # Now insert 50 tokens into the 'user_tokens' table for the new user
        insert_tokens_stmt = tables.user_tokens.insert().values(
            user_id=new_user_id,
            total_tokens=100,  # Give the user 50 free tokens initially
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.execute(insert_tokens_stmt)
        db.commit()

        # Return a custom response for successful user registration
        app_response.set_response(AppConstants.CREATE_SUCCESSFUL, {}, Messages.USER_CREATED_SUCCESSFULLY, True)
        return app_response

    except Exception as e:
        db.rollback()
        # Handle unexpected errors
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR, {}, Messages.SOMETHING_WENT_WRONG, False)
        return app_response
    

def login_service(form_data, db: Session):
    query = tables.users.select().where(tables.users.c.email == form_data.username)
    user = db.execute(query).fetchone()

    if not user:
        #raise HTTPException(status_code=404, detail="Email not found.")
        app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.NOT_FOUND_USER_DETAILS, False)
        return app_response 


    if not verify_password(form_data.password, user.password):
        app_response.set_response(AppConstants.UNAUTHORIZED_ACCESS, {}, Messages.INCORRECT_PASSWORD, False)
        return app_response 
        

    access_token = create_access_token(data={"sub": user.email},expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    app_response.set_response(AppConstants.UNAUTHORIZED_ACCESS, {"id": user.id,
        "access_token": access_token,
        "token_type": "bearer"}, Messages.LOGIN_SUCCESSFUL, True)
    return app_response


async def forgot_password_service(request, db: Session, background_tasks: BackgroundTasks):
    try:
        query = tables.users.select().where(tables.users.c.email == request.email)
        user = db.execute(query).fetchone()
   
        if not user:
            return app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.EMAIL_NOT_FOUND, False)


        otp = generate_otp()
        expiry_time = datetime.utcnow() + timedelta(minutes=10)

        # Insert OTP into the database
        insert_stmt = tables.user_otps.insert().values(
            user_id=user.id, otp_code=otp, expires_at=expiry_time
        )
        try:
            db.execute(insert_stmt)
            db.commit()
        except Exception as db_error:
            app_response.set_response(AppConstants.UNSUCCESSFULL_STATUS_CODE,{}, Messages.DATABASE_ERROR, False)
            return app_response

        # Prepare email body content
        email_body = f"""
        <html>
            <body>
                <h3>Reset Your Password</h3>
                <p>Your OTP is: <b>{otp}</b></p>
                <p>This OTP will expire in 10 minutes.</p>
            </body>
        </html>
        """

        background_tasks.add_task(send_email, request.email, "Reset Your Password", email_body)
        app_response.set_response(AppConstants.SUCCESSFULL_STATUS_CODE,{}, Messages.OTP_SEND_SUCCESSFUL, True)
        return app_response
    
    except Exception as e:
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR,{}, Messages.SERVER_ERROR, False)
        return app_response

def reset_password_service(request, db: Session):
    user_query = tables.users.select().where(tables.users.c.email == request.email)
    user = db.execute(user_query).fetchone()

    if not user:
        app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.USER_NOT_FOUND, False)
        return app_response    

    query = tables.user_otps.select().where(
        (tables.user_otps.c.user_id == user.id) & 
        (tables.user_otps.c.otp_code == request.otp)
    )
    otp_entry = db.execute(query).fetchone()

    if not otp_entry:
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.OTP_INVALID, False)
        return app_response 

    if datetime.utcnow() > otp_entry.expires_at:
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.OTP_EXPIRED, False)
        return app_response

    hashed_password = hash_password(request.new_password)
    update_stmt = tables.users.update().where(
        tables.users.c.id == user.id
    ).values(password=hashed_password)

    db.execute(update_stmt)
    db.commit()

    db.execute(tables.user_otps.delete().where(tables.user_otps.c.user_id == user.id))
    db.commit()

    app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.PASSWORD_RESET_SUCCESSFUL, True)
    return app_response



def change_password_service(request, db: Session):
    try:
        
        # 1. Check if old password matches the one in the database
        query = tables.users.select().where(tables.users.c.email  == request.email)
        user = db.execute(query).fetchone()

        if not user:
            app_response.set_response(AppConstants.DATA_NOT_FOUND, {}, Messages.NOT_FOUND_USER_DETAILS, False)
            return app_response

        # Verify the old password
        if not verify_password(request.current_password, user.password):
            app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.INCORRECT_OLD_PASSWORD, False)
            return app_response

        # 2. Ensure new password and confirm password match
        if request.new_password != request.confirm_password:
            app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.PASSWORDS_DO_NOT_MATCH, False)
            return app_response

        # 3. Ensure new password is not the same as the old password
        if request.current_password == request.new_password:
            app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.NEW_PASSWORD_SAME_AS_OLD, False)
            return app_response

        # 4. Hash the new password
        hashed_new_password = hash_password(request.new_password)

        # 5. Update the password in the database
        update_stmt = tables.users.update().where(tables.users.c.email == request.email).values(
            password=hashed_new_password, updated_at=datetime.utcnow()
        )
        db.execute(update_stmt)
        db.commit()

        # Return success message
        app_response.set_response(AppConstants.PASSWORD_CHANGE_SUCCESS, {}, Messages.PASSWORD_CHANGED_SUCCESSFULLY, True)
        return app_response

    except IntegrityError as e:
        db.rollback()
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR, {}, f"Integrity error: {str(e)}", False)
        return app_response
    except Exception as e:
        db.rollback()
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR, {}, f"An unexpected error occurred: {str(e)}", False)
        return app_response

