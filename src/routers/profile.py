
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.configs.config import get_db
from src.services.profile import get_student_profile_service ,update_student_profile_service
from src.schemas.profile import UpdateStudentProfileSchema
from src.configs.utilites import get_current_user
from fastapi import BackgroundTasks
from src.common.app_response import AppResponse
from src.common.app_constants import AppConstants
from src.common.messages import Messages



router = APIRouter()
app_response = AppResponse()


@router.get("/profile/{user_id}")
async def get_student_profile(user_id: str, db: Session = Depends(get_db)):
    """
    API to fetch student profile details.
    """
    return get_student_profile_service(user_id, db)



@router.put("/update-profile/{user_id}")
async def update_student_profile(
    user_id: str,
    request: UpdateStudentProfileSchema,
    db: Session = Depends(get_db)
):
    return update_student_profile_service(user_id, request, db)