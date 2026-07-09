import requests

# This simulates what Safaricom sends to your server
payload = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "test_id",
            "CheckoutRequestID": "test_checkout",
            "ResultCode": 0,
            "CallbackMetadata": {
                "Item": [{"Name": "PhoneNumber", "Value": "jpcyberservices@gmail.com"}] # Use the email/ID you use in your DB
            }
        }
    }
}

# Replace this with the local URL your FastAPI/Flask app is running on
# e.g., http://localhost:8000/mpesa-callback
response = requests.post("http://localhost:8000/mpesa-callback", json=payload)
print(response.json())