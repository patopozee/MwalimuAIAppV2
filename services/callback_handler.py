# services/callback_handler.py
from fastapi import FastAPI, Request
from services.database import db # Direct reference to your Firestore client
from datetime import datetime, timedelta
import collections

app = FastAPI()
PAYMENT_AUDIT_LOGS = collections.deque(maxlen=20)


@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    
    # -----------------------------------------------------------------
    # FIX 2: Append every inbound raw callback payload directly to logs
    # -----------------------------------------------------------------
    PAYMENT_AUDIT_LOGS.append({
        "timestamp": datetime.utcnow().isoformat(), 
        "payload": data
    })
    
    body = data.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    
    # 1. Check if the payment transaction succeeded
    if result_code == 0:
        metadata = body.get("CallbackMetadata", {}).get("Item", [])

        # ----------------------------------------------------------
        # Extract transaction details from Safaricom callback
        # ----------------------------------------------------------
        phone = next(
            (str(item["Value"]) for item in metadata if item["Name"] == "PhoneNumber"),
            None
        )

        mpesa_receipt = next(
            (str(item["Value"]) for item in metadata if item["Name"] == "MpesaReceiptNumber"),
            "MPESA_REF"
        )

        checkout_request_id = body.get("CheckoutRequestID")

        if not checkout_request_id:
            print("❌ Callback missing CheckoutRequestID.")
            return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}

        # ----------------------------------------------------------
        # Retrieve pending payment
        # ----------------------------------------------------------
        payment_doc = (
            db.collection("pending_payments")
            .document(checkout_request_id)
            .get()
        )

        if not payment_doc.exists:
            print(f"❌ Pending payment not found: {checkout_request_id}")
            return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}

        payment = payment_doc.to_dict()

        if payment is None:
            print("❌ Pending payment document is empty.")
            return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}

        uid = payment.get("uid")
        plan = payment.get("plan")

        if not uid or not plan:
            print("❌ Pending payment missing uid or plan.")
            return {"ResponseCode": "0", "ResponseDesc": "Accept Success"}

        # ----------------------------------------------------------
        # Activate subscription
        # ----------------------------------------------------------
        expiry = (
            datetime.utcnow() + timedelta(days=30)
        ).strftime("%Y-%m-%d")

        db.collection("users").document(uid).update({
            "subscription": {
                "tier": plan,
                "expiry_date": expiry,
                "payment_status": "Completed",
                "reference_id": mpesa_receipt,
                "updated_at": datetime.utcnow().isoformat()
            }
        })

        # ----------------------------------------------------------
        # Delete pending payment
        # ----------------------------------------------------------
        db.collection("pending_payments") \
            .document(checkout_request_id) \
            .delete()

        print(f"✅ Activated '{plan}' subscription for user '{uid}'")