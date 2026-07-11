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
        
        # Extract the phone number and transaction reference cleanly
        phone = next((str(item['Value']) for item in metadata if item['Name'] == 'PhoneNumber'), None)
        mpesa_receipt = next((str(item['Value']) for item in metadata if item['Name'] == 'MpesaReceiptNumber'), "MPESA_REF")
        
        if phone:
            # 2. Search Firestore for the user record with this phone number
            users_ref = db.collection('users')
            query = users_ref.where('phone', '==', phone).limit(1).stream()
            
            user_doc_id = None
            for doc in query:
                user_doc_id = doc.id
                break
                
            # 3. If found by phone, atomically commit subscription updates
            if user_doc_id:
                calculated_expiry = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
                
                live_subscription = {
                    "tier": "Mwalimu AI Plus",
                    "expiry_date": calculated_expiry,
                    "payment_status": "Completed",
                    "reference_id": mpesa_receipt,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # Directly execute the update payload using the real Document ID
                db.collection('users').document(user_doc_id).update({
                    "subscription": live_subscription
                })
                print(f"🎉 Successfully upgraded User ID {user_doc_id} via M-Pesa phone: {phone}")
            else:
                print(f"⚠️ M-Pesa payment received from {phone}, but no matching student profile was found.")
                
    return {"ResponseCode": "0", "ResponseDesc": "Accept Success"} # Confirms receipt to Safaricom

@app.get("/mpesa-audit-vault")
async def get_payment_audit_vault():
    """Secure endpoint displaying real-time inbound raw payment drop histories."""
    return list(PAYMENT_AUDIT_LOGS)
