from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import razorpay
from fastapi.middleware.cors import CORSMiddleware
import logging

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
client.set_app_details({"title" : "pay", "version" : "1.0"})

# Define data model for payment request
class PaymentRequest(BaseModel):
    amount: int
    currency: str
    receipt: str

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"New request: {request.method} {request.url}")
    response = await call_next(request)
    logging.info(f"Completed request: {response.status_code}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
