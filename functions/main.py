# type: ignore
from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore

# Initialize Firebase
initialize_app()
db = firestore.client()

@https_fn.on_request()
def mpesa_callback(req: https_fn.Request) -> https_fn.Response:
    # 1. Parse JSON body
    data = req.get_json()
    if not data:
        return https_fn.Response("No data received", status=400)

    # 2. Extract STK Callback data
    stk_callback = data.get("Body", {}).get("stkCallback", {})
    
    # 3. Check for Success (ResultCode 0 is success)
    if stk_callback.get("ResultCode") == 0:
        checkout_id = stk_callback.get("CheckoutRequestID")
        
        # 4. Update Firestore
        # This looks for the user who initiated this specific checkout
        users_ref = db.collection('users').where('last_checkout_id', '==', checkout_id).stream()
        for doc in users_ref:
            doc.reference.update({'tier': 'Premium'})
            
    # 5. Return success to Safaricom
    return https_fn.Response("Accepted", status=200)