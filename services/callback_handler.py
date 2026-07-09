# Create a new file, e.g., callback_handler.py
from fastapi import FastAPI, Request
from services.database import upgrade_user_tier

app = FastAPI()

@app.post("/mpesa-callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    
    # M-Pesa sends a 'ResultCode' of 0 for success
    body = data.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    
    if result_code == 0:
        # Extract the user's phone or identifier from the callback
        # You need to pass this identifier in the STKPush request
        # 'AccountReference' or similar metadata field
        metadata = body.get("CallbackMetadata", {}).get("Item", [])
        # Find the customer phone number in the metadata
        phone = next((item['Value'] for item in metadata if item['Name'] == 'PhoneNumber'), None)
        
        # Now upgrade the user
        # Note: You need a way to map 'phone' to 'uid'
        upgrade_user_tier(phone, "Mwalimu AI Plus")
        
    return {"status": "success"}