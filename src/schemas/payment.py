from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from enum import Enum

# Enum for payment status
class PaymentStatusEnum(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"  # Added refunded status for completeness

# Schema for initiating or continuing a payment
class PaymentRequest(BaseModel):
    user_id: UUID
    plan_id: int
    currency: str = "USD"  

    class Config:
        str_strip_whitespace = True  # Automatically strips whitespace from strings

# Schema for Payment Execution Response (from PayPal after user approval)
class PaymentExecutionResponse(BaseModel):
    payment_id: str
    payer_id: str
    payment_status: PaymentStatusEnum
    amount: Decimal
    currency: str
    tokens_purchased: int
    transaction_id: str
    created_at: datetime

# Schema for the payment details (without ORM)
class PaymentDetails(BaseModel):
    transaction_id: str
    user_id: UUID
    amount: Decimal
    tokens_purchased: int
    payment_status: PaymentStatusEnum
    created_at: datetime

class UserResponseModel(BaseModel):
    id: int
    username: str
    email: str

class PaymentResponse(BaseModel):
    order_id: str
    paypal_capture_id: str
    amount: float
    status: str
    payer_email: str
    created_at: str  # Timestamp or string format

class PayPalReturnRequest(BaseModel):
    token: str
    payer_id: str
    

