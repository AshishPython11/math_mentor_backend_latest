from sqlalchemy.orm import Session
from src.services.tables import Tables
from src.common.app_response import AppResponse
from sqlalchemy import select, update
from src.common.app_constants import AppConstants
from src.common.messages import Messages
from datetime import datetime, date

app_response = AppResponse()
tables = Tables()



def get_student_profile_service(user_id: str, db):
    """
    Fetch student profile details using dynamically loaded table metadata.
    """
    try:
        query = select(
            tables.users.c.name,
            tables.users.c.email,
            tables.users.c.grade,
            tables.users.c.birth_date,
            tables.users.c.created_at,
            tables.users.c.is_paid
        ).where(tables.users.c.id == user_id)

        user = db.execute(query).fetchone()

        if not user:
            app_response.set_response(AppConstants.USER_NOT_FOUND, {}, Messages.USER_NOT_FOUND, False)
            return app_response

        def format_birth_date(date_value):
            if not date_value:
                return None
            if isinstance(date_value, str):
                return date_value
            return date_value.strftime("%d-%m-%Y")

        def format_member_since(date_value):
            return date_value.strftime("%B %d, %Y") if isinstance(date_value, datetime) else None

        student_data = {
            "name": user.name,
            "email": user.email,
            "grade": user.grade,
            "birth_date": format_birth_date(user.birth_date),
            "member_since": format_member_since(user.created_at),
            "is_paid": user.is_paid
        }

        app_response.set_response(AppConstants.CODE_SUCCESS, student_data, Messages.SUCCESS, True)
        return app_response

    except Exception as e:
        app_response.set_response(AppConstants.CODE_INTERNAL_SERVER_ERROR, {}, Messages.SOMETHING_WENT_WRONG, False)
        return app_response




def update_student_profile_service(user_id: str, request, db):
    # Convert the Pydantic model to dictionary
    request_data = request.model_dump()  

    # Extract grade and birth_date
    new_grade = request_data.get("grade")
    new_birth_date = request_data.get("birth_date")

    update_data = {}

    if new_grade:
        update_data["grade"] = new_grade

    if new_birth_date:
        if isinstance(new_birth_date, date):  # If already a date object
            parsed_date = new_birth_date
        elif isinstance(new_birth_date, str) and len(new_birth_date) == 10 and new_birth_date[2] == '-' and new_birth_date[5] == '-':  # Check the format "DD-MM-YYYY"
            day, month, year = new_birth_date.split('-')
            if len(day) == 2 and len(month) == 2 and len(year) == 4:
                parsed_date = datetime.strptime(new_birth_date, "%d-%m-%Y").date()
            else:
                # Invalid date format
                app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, "Invalid date format. Use DD-MM-YYYY.", False)
                return app_response
        else:
            # Invalid date format or type
            app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, "Invalid date format. Use DD-MM-YYYY.", False)
            return app_response

        update_data["birth_date"] = parsed_date

    if not update_data:
        # Custom response when there's no data to update
        app_response.set_response(AppConstants.CODE_INVALID_REQUEST, {}, Messages.VALIDATE_DATA, False)
        return app_response

    # Perform the update in the database
    stmt = update(tables.users).where(tables.users.c.id == user_id).values(**update_data)
    result = db.execute(stmt)
    db.commit()

    if result.rowcount == 0:
        # Custom response when user is not found
        app_response.set_response(AppConstants.USER_NOT_FOUND, {}, Messages.USER_NOT_FOUND, False)
        return app_response

    # Success response
    app_response.set_response(AppConstants.CODE_SUCCESS, {}, "Profile updated successfully", True)
    return app_response
