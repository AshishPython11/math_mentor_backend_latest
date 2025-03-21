from pydantic import BaseModel, EmailStr, Field, validator, HttpUrl ,field_validator
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, UUID4
import re


class UpdateStudentProfileSchema(BaseModel):
    grade: Optional[int] = Field(None, description="Student's grade")
    birth_date: Optional[date] = Field(None, description="Date of birth (DD-MM-YYYY)")

    @field_validator("birth_date", mode="before")
    @classmethod
    def validate_birth_date(cls, value: str | date):
        if isinstance(value, date):  
            return value
        try:
            return datetime.strptime(value, "%d-%m-%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD-MM-YYYY.")
