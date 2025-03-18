import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import requests
from datetime import datetime
from uuid import uuid4
from src.configs.settings import settings
from src.services.tables import Tables
from src.configs.config import get_db
from sqlalchemy import select, update
from src.schemas.payment import *

# Initialize tables and router
tables = Tables()
router = APIRouter()

# PayPal API Configuration
PAYPAL_CLIENT_ID = settings.PAYPAL_CLIENT_ID
PAYPAL_SECRET = settings.PAYPAL_CLIENT_SECRET
PAYPAL_API_BASE_URL = settings.PAYPAL_API_BASE_URL

# Logger Configuration
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("payment.log"),  # Log to a file
        logging.StreamHandler()  # Log to the console
    ]
)

def get_paypal_oauth_token() -> str:
    """Obtain PayPal OAuth token with retry logic"""
    try:
        logger.info("Fetching PayPal OAuth token...")
        response = requests.post(
            f"{PAYPAL_API_BASE_URL}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        logger.info("Successfully fetched PayPal OAuth token.")
        return response.json()["access_token"]
    except requests.HTTPError as e:
        logger.error(f"OAuth token error: {e.response.text}")
        raise HTTPException(500, "PayPal authentication failed")

def get_order_details(order_id: str) -> dict:
    """Retrieve PayPal order details"""
    url = f"{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}"
    headers = {"Authorization": f"Bearer {get_paypal_oauth_token()}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        logger.error(f"Order details failed: {e.response.text}")
        raise HTTPException(e.response.status_code, "Failed to retrieve order details")

def capture_paypal_order(order_id: str) -> dict:
    """Capture a PayPal order only if approved"""
    try:
        logger.info(f"Capturing PayPal order: {order_id}")
        
        # Get PayPal OAuth token
        auth_token = get_paypal_oauth_token()
        
        # Configure headers (ONLY Authorization)
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"  # Ensure proper content type
        }
        
        # Capture request body (this should be an empty object for a basic capture)
        capture_data = {}

        # Make the capture request
        url = f"{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}/capture"
        response = requests.post(url, headers=headers, json=capture_data)  # Note the `json=capture_data`
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        logger.info(f"Successfully captured PayPal order: {response.json()}")
        return response.json()
    
    except requests.HTTPError as e:
        logger.error(f"Capture failed: {e.response.text}")
        raise HTTPException(500, "Payment capture failed")



def create_paypal_order(amount: float, tokens: int, reference_id: str) -> tuple:
    """Create PayPal order and return (approval_url, paypal_order_id)"""
    try:
        logger.info(f"Creating PayPal order for reference_id: {reference_id}, amount: {amount}, tokens: {tokens}")
        response = requests.post(
            f"{PAYPAL_API_BASE_URL}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {get_paypal_oauth_token()}",
                "Content-Type": "application/json"
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": reference_id,
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{amount:.2f}"  # Ensure 2 decimal places
                    },
                    "description": f"Purchase {tokens} tokens"
                }],
                "application_context": {
                    "return_url": "http://localhost:8000/paypal/return",
                    "cancel_url": "http://localhost:8000/paypal/cancel"
                }
            }
        )
        response.raise_for_status()  # This will trigger an HTTPError for 4xx/5xx responses
        data = response.json()
        approval_url = next(l["href"] for l in data["links"] if l["rel"] == "approve")
        paypal_order_id = data["id"]
        logger.info(f"Successfully created PayPal order. Approval URL: {approval_url}")
        return approval_url, paypal_order_id
    except requests.HTTPError as e:
        # Log the full error response from PayPal
        logger.error(f"PayPal order creation failed. Status: {e.response.status_code}, Response: {e.response.text}")
        raise HTTPException(500, f"PayPal order creation failed: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(500, "Payment initiation failed")
    

@router.post("/payments/start")
async def start_payment(request: PaymentRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Starting payment for user_id: {request.user_id}, plan_id: {request.plan_id}")

        # Validate user exists
        user_exists = db.execute(
            select(tables.users.c.id).where(tables.users.c.id == request.user_id)
        ).scalar()
        if not user_exists:
            logger.error(f"User not found: {request.user_id}")
            raise HTTPException(404, "User not found")

        # Fetch plan details
        plan = db.execute(
            select(tables.plans.c.amount, tables.plans.c.tokens).where(tables.plans.c.id == request.plan_id)
        ).fetchone()

        if not plan:
            logger.error(f"Plan not found: {request.plan_id}")
            raise HTTPException(404, "Plan not found")

        amount, tokens_purchased = plan.amount, plan.tokens
        logger.info(f"Fetched plan details: amount={amount}, tokens={tokens_purchased}")

        # Generate unique reference ID
        reference_id = f"PYPL-{uuid4().hex[:14]}"
        logger.info(f"Generated reference_id: {reference_id}")

        # Create PayPal order
        approval_url, paypal_order_id = create_paypal_order(
            amount=float(amount),  # Convert Decimal to float
            tokens=tokens_purchased,
            reference_id=reference_id
        )

        # Insert payment record
        db.execute(
            tables.payments.insert().values(
                user_id=request.user_id,
                plan_id=request.plan_id,
                amount=amount,
                tokens_purchased=tokens_purchased,
                paypal_order_id=paypal_order_id,
                payment_status="pending",
                created_at=datetime.now()
            )
        )
        db.commit()
        logger.info(f"Payment record created for paypal_order_id: {paypal_order_id}")

        return {"payment_url": approval_url}

    except Exception as e:
        logger.error(f"Payment start failed: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Payment initiation failed: {str(e)}")







@router.post("/paypal/return")
async def paypal_return(request: PayPalReturnRequest, db: Session = Depends(get_db)):
    try:
        # Access token and payer_id from Pydantic model
        token = request.token
        payer_id = request.payer_id

        logger.info(f"Processing PayPal return for paypal_order_id: {token}")

        # 1. Get order details
        order_details = get_order_details(token)
        logger.info(f"Order status: {order_details['status']}")

        # 2. Handle approved or completed status
        if order_details["status"] not in ["APPROVED", "COMPLETED"]:
            logger.error(f"Order not approved. Status: {order_details['status']}")
            return {"error": "User did not approve the payment"}

        # 3. Capture the payment only if status is APPROVED
        capture_response = capture_paypal_order(token)
        capture_id = capture_response["purchase_units"][0]["payments"]["captures"][0]["id"]
        
        # Correct place to get the transaction ID
        transaction_id = capture_response["purchase_units"][0]["payments"]["captures"][0]["id"]

        # 4. Update database with capture_id and transaction_id
        logger.info(f"Updating database with capture_id: {capture_id} and transaction_id: {transaction_id}")
        db.execute(
            update(tables.payments)
            .where(tables.payments.c.paypal_order_id == token)  # Now matches PayPal's order ID
            .values(
                payment_status="completed",
                paypal_capture_id=capture_id,
                paypal_transaction_id=transaction_id,
                updated_at=datetime.now()
            )
        )
        db.commit()
        logger.info(f"Payment status updated to 'completed' for paypal_order_id: {token}")

        return {"status": "success", "order_id": token, "capture_id": capture_id, "transaction_id": transaction_id}
    except Exception as e:
        logger.error(f"Return processing failed: {str(e)}")
        raise HTTPException(500, detail=str(e))








    
@router.get("/paypal/cancel")
async def handle_paypal_cancel(token: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"Handling PayPal cancel for token: {token}")
        
        db.execute(
            update(tables.payments)
            .where(tables.payments.c.paypal_order_id == token)
            .values(payment_status="canceled")
        )
        db.commit()
        logger.info(f"Payment status updated to 'canceled' for order_id: {token}")
        return {"status": "canceled", "order_id": token}
    except Exception as e:
        logger.error(f"Cancel handling failed: {str(e)}")
        db.rollback()
        raise HTTPException(500, "Cancel processing failed")





@router.get("/payments/user/{user_id}")
async def get_user_payments(user_id: UUID, db: Session = Depends(get_db)):
    try:
        # Fetch all payments for the given user
        payments = db.execute(
            select(tables.payments).where(tables.payments.c.user_id == user_id)
        ).fetchall()

        # If no payments found, raise a 404 error
        if not payments:
            raise HTTPException(status_code=404, detail="No payments found for this user")

        # Return the payments as a list of dictionaries by converting each row to a dict
        return {"payments": [dict(payment._mapping) for payment in payments]}

    except Exception as e:
        # If an exception occurs, raise a 400 error
        raise HTTPException(status_code=400, detail=f"Error fetching user payments: {str(e)}")



@router.get("/payments/status/all")
async def get_payments_by_status(db: Session = Depends(get_db)):
    try:
        # Fetch all payments where payment_status is either 'free' or 'completed'
        payments = db.execute(
            select(tables.payments).where(
                tables.payments.c.payment_status.in_(['free', 'completed'])
            )
        ).fetchall()

        # If no payments found, raise a 404 error
        if not payments:
            raise HTTPException(status_code=404, detail="No payments found")

        # Return payments as a list of dictionaries
        return {"payments": [dict(payment._mapping) for payment in payments]}

    except Exception as e:
        # If an exception occurs, raise a 400 error
        raise HTTPException(status_code=400, detail=f"Error fetching payments: {str(e)}")






