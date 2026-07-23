import base64
from datetime import datetime

import requests
import streamlit as st
from datetime import datetime, timedelta
from services.firebase_init import db


class MpesaPaymentService:

    TOKEN_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    STK_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    @staticmethod
    def normalize_phone(phone: str) -> str:
        phone = str(phone).strip().replace(" ", "").replace("-", "")

        if phone.startswith("+254"):
            phone = phone[1:]

        elif phone.startswith("254"):
            pass

        elif phone.startswith("0"):
            phone = "254" + phone[1:]

        return phone

    @staticmethod
    def generate_token():

        consumer_key = st.secrets["mpesa"]["consumer_key"]
        consumer_secret = st.secrets["mpesa"]["consumer_secret"]

        try:

            response = requests.get(
                MpesaPaymentService.TOKEN_URL,
                auth=(consumer_key, consumer_secret),
                timeout=15,
            )

            if response.status_code != 200:
                return None

            return response.json()["access_token"]

        except Exception as e:
            return None

    @staticmethod
    def initiate_stk_push(phone_number, amount, uid=None, plan="premium"):
        

        token = MpesaPaymentService.generate_token()

        if token is None:
            return {
                "success": False,
                "error": "Failed to generate OAuth token."
            }

        phone_number = MpesaPaymentService.normalize_phone(phone_number)

        shortcode = str(st.secrets["mpesa"]["shortcode"])
        passkey = str(st.secrets["mpesa"]["passkey"])
        callback = st.secrets["mpesa"]["callback_url"]

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        password_string = shortcode + passkey + timestamp
        password = base64.b64encode(password_string.encode()).decode()
        

        payload = {
            "BusinessShortCode": shortcode, # Use the variable from secrets
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": shortcode,            # Use the variable from secrets
            "PhoneNumber": phone_number,
            "CallBackURL": callback,        # Use the variable from secrets
            "AccountReference": "Mwalimu AI App",
            "TransactionDesc": f"Mwalimu AI {plan.title()} Subscription"
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:

            response = requests.post(
                MpesaPaymentService.STK_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )

            data = response.json()

            if response.status_code == 200:

                if data.get("ResponseCode") == "0":
                    # Save pending payment details
                    if uid:
                        db.collection("pending_payments").document(
                            data.get("CheckoutRequestID")
                        ).set({
                            "uid": uid,
                            "plan": plan,
                            "amount": amount,
                            "phone": phone_number,
                            "created_at": datetime.utcnow().isoformat()
                        })

                    return {
                        "success": True,
                        "merchant_request_id": data.get("MerchantRequestID"),
                        "checkout_request_id": data.get("CheckoutRequestID"),
                        "customer_message": data.get("CustomerMessage"),
                    }

                return {
                    "success": False,
                    "error": data.get(
                        "ResponseDescription",
                        data.get("errorMessage", "Unknown M-Pesa error"),
                    ),
                }

            return {
                "success": False,
                "error": data.get("errorMessage", response.text),
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
            }
        
    @staticmethod
    def check_transaction_status(checkout_request_id):
        token = MpesaPaymentService.generate_token()
        if not token:
            return {"completed": False, "error": "Token failed"}

        shortcode = str(st.secrets["mpesa"]["shortcode"])
        passkey = str(st.secrets["mpesa"]["passkey"])
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        password_string = shortcode + passkey + timestamp
        password = base64.b64encode(password_string.encode()).decode()

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
                json=payload,
                headers=headers,
                timeout=30
            )
            data = response.json()
            
            # ResultCode 0 means successful transaction complete
            if data.get("ResultCode") == "0":
                return {"completed": True}
            elif data.get("ResultCode"):
                return {"completed": False, "failed": True}
                
            return {"completed": False}
        except Exception as e:
            return {"completed": False, "error": str(e)}
        
    @staticmethod
    def upgrade_user_subscription(uid, tier_name):
        """
        Updates the user's subscription tree in Firestore.
        """
        try:
            # Set expiry to 30 days from now
            expiry_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Update only the specific fields inside the 'subscription' map
            db.collection("users").document(uid).update({
                "subscription.tier": tier_name,
                "subscription.start_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "subscription.expiry_date": expiry_date
            })
            return {"success": True}
        except Exception as e:
            print(f"Error upgrading subscription: {e}")
            return {"success": False, "error": str(e)}

    