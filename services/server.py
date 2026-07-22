# server.py
from fastapi import FastAPI, Request
from services.payment_service import MpesaPaymentService
from services.firebase_init import db

app = FastAPI()

@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    try:
        body = await request.json()
        
        stk_callback = body.get("Body", {}).get("STKCallback", {})
        result_code = stk_callback.get("ResultCode")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        
        pending_ref = db.collection("pending_payments").document(checkout_request_id)
        pending_doc = pending_ref.get()
        
        if not pending_doc.exists:
            return {"ResultCode": 1, "ResultDesc": "Pending payment record not found"}
            
        # Add 'or {}' to satisfy Pylance that this is always a dictionary
        payment_data = pending_doc.to_dict() or {}
        uid = payment_data.get("uid")
        plan = payment_data.get("plan")
        
        if result_code == 0:
            MpesaPaymentService.upgrade_user_subscription(uid, plan)
            pending_ref.delete()
        else:
            pending_ref.delete()
            
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        print(f"Error handling mpesa callback: {e}")
        return {"ResultCode": 1, "ResultDesc": str(e)}