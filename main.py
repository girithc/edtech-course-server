from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import razorpay
from fastapi.middleware.cors import CORSMiddleware
import logging
import httpx
import json

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Razorpay client
client = razorpay.Client(auth=("rzp_test_GzlLiqxhBQXN0G", "yztvsf7aTqR0imUb2x51kMjE"))
client.set_app_details({"title": "pay", "version": "1.0"})

# Define data models for payment request
class PaymentRequest(BaseModel):
    amount: int
    currency: str
    receipt: str

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_body = await request.body()
    logging.info(f"New request: {request.method} {request.url}")
    logging.info(f"Request body: {request_body.decode('utf-8')}")

    response = await call_next(request)

    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    # Replace response with new content
    response = Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )

    logging.info(f"Completed request with status: {response.status_code}")
    logging.info(f"Response body: {response_body.decode('utf-8')}")

    return response


@app.post("/pay/")
def create_payment(request: PaymentRequest):
    try:
        logging.info(f"Received payment request: {request}")
        data = {
            "amount": request.amount,
            "currency": request.currency,
            "receipt": request.receipt,
        }
        payment = client.order.create(data=data)
        logging.info(f"Payment created: {payment}")
        return payment
    except Exception as e:
        logging.error(f"Error creating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class PhoneRequest(BaseModel):
    phone: str

class PhoneNumber(BaseModel):
    phone: str

class SendOTPResponse(BaseModel):
    type: str
    request_id: str


class VerifyOTPResponse(BaseModel):
    type: str
    message: str

class Customer(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    # Add other customer fields as needed

class CustomerLogin(BaseModel):
    customer: Customer
    message: str
    type: str

# Mock function to simulate database interactions
async def get_customer_by_phone(phone: str, fcm: str) -> Customer:
    # Implement the actual database logic here
    return Customer(id=1, name="Test User", phone=phone, email="test@example.com")

@app.post("/send-otp")
async def send_otp(phone_number: PhoneNumber):
    # Print the received phone number to the terminal

    phone = phone_number.phone
    
    if phone == "1234567890":
        return SendOTPResponse(type="test", request_id="test")

    try:
        url = f"https://control.msg91.com/api/v5/otp?template_id=6562ddc2d6fc0517bc535382&mobile=91{phone}"
        headers = {
            "accept": "application/json",
            "authkey": "405982AVwwWkcR036562d3eaP1",
            "content-type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logging.info(f"Response from MSG91 API: {data}")

        return SendOTPResponse(**data)
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTPStatusError: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-otp", response_model=CustomerLogin)
async def verify_otp(phone: str, otp: int, fcm: str):
    if phone == "1234567890":
        otpresponse = VerifyOTPResponse(type="success", message="test user - OTP verified successfully")
        customer = await get_customer_by_phone(phone, fcm)
        return CustomerLogin(customer=customer, message=otpresponse.message, type=otpresponse.type)

    try:
        url = f"https://control.msg91.com/api/v5/otp/verify?mobile=91{phone}&otp={otp}"
        headers = {
            "accept": "application/json",
            "authkey": "405982AVwwWkcR036562d3eaP1"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            otpresponse = VerifyOTPResponse(**response.json())

        if otpresponse.type == "success":
            customer = await get_customer_by_phone(phone, fcm)
            return CustomerLogin(customer=customer, message=otpresponse.message, type=otpresponse.type)
        else:
            raise HTTPException(status_code=400, detail="OTP verification failed")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
