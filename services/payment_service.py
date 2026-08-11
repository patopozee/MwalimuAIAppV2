import base64
from datetime import datetime, timedelta
import requests
import streamlit as st
from services.firebase_init import db


class MpesaPaymentService:

    # =========================================================
    # PRODUCTION ENDPOINTS (Replaced sandbox URLs)
    # =========================================================
    TOKEN_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    STK_URL = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    QUERY_URL = "https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query"

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
        try:
            consumer_key = st.secrets["mpesa"]["consumer_key"]
            consumer_secret = st.secrets["mpesa"]["consumer_secret"]

            response = requests.get(
                MpesaPaymentService.TOKEN_URL,
                auth=(consumer_key, consumer_secret),
                timeout=15,
            )

            if response.status_code != 200:
                return None, f"HTTP {response.status_code}: {response.text}"

            token = response.json().get("access_token")
            return token, None

        except Exception as e:
            return None, str(e)

    @staticmethod
    def initiate_stk_push(phone_number, amount, uid=None, plan="premium"):
        token, err = MpesaPaymentService.generate_token()

        if not token:
            return {"success": False, "message": f"OAuth Generation Failed: {err}"}

        phone_number = MpesaPaymentService.normalize_phone(phone_number)

        shortcode = str(st.secrets["mpesa"]["shortcode"])  # This reads 4343165
        passkey = str(st.secrets["mpesa"]["passkey"])
        callback = st.secrets["mpesa"]["callback_url"]
        
        # 🚨 READS YOUR TILL NUMBER FROM SECRETS TO MAP CASH STREAMING PATHS
        till_number = str(st.secrets["mpesa"]["till_number"]) 

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_string = shortcode + passkey + timestamp
        password = base64.b64encode(password_string.encode()).decode()

        # =========================================================
        # PROPER PAYLOAD STRUCT FOR BUY GOODS TILLS
        # =========================================================
        payload = {
            "BusinessShortCode": shortcode,              # Keep as 4343165
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerBuyGoodsOnline", # Keep unchanged
            "Amount": int(amount),
            "PartyA": phone_number,                      
            "PartyB": till_number,                       # 🚨 MUST BE YOUR ACTUAL TILL NUMBER
            "PhoneNumber": phone_number,                 
            "CallBackURL": callback,
            "AccountReference": "Mwalimu AI App",
            "TransactionDesc": f"Mwalimu AI App {plan.title()} Subscription"
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

            if response.status_code == 200 and data.get("ResponseCode") == "0":

                print("========== MPESA STK ACCEPTED ==========")
                print("HTTP:", response.status_code)
                print("Response:", data)
                print("BusinessShortCode:", payload["BusinessShortCode"])
                print("TransactionType:", payload["TransactionType"])
                print("PartyA:", payload["PartyA"])
                print("PartyB:", payload["PartyB"])
                print("PhoneNumber:", payload["PhoneNumber"])
                print("CallbackURL:", payload["CallBackURL"])
                print("CheckoutRequestID:", data.get("CheckoutRequestID"))
                print("MerchantRequestID:", data.get("MerchantRequestID"))
                print("CustomerMessage:", data.get("CustomerMessage"))
                print("========================================")

                if uid:
                    db.collection("pending_payments").document(
                        data.get("CheckoutRequestID")
                    ).set({
                        "uid": uid,
                        "plan": plan,
                        "amount": amount,
                        "phone": phone_number,
                        "checkout_request_id": data.get("CheckoutRequestID"),
                        "merchant_request_id": data.get("MerchantRequestID"),
                        "created_at": datetime.utcnow().isoformat()
                    })

                return {
                    "success": True,
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "checkout_request_id": data.get("CheckoutRequestID"),
                    "customer_message": data.get("CustomerMessage"),
                }

            error_msg = data.get("errorMessage") or data.get("ResponseDescription") or response.text
            return {
                "success": False,
                "message": f"Daraja Error ({response.status_code}): {error_msg}"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Server Exception: {str(e)}"
            }

    @staticmethod
    def check_transaction_status(checkout_request_id):
        token, err = MpesaPaymentService.generate_token()
        if not token:
            return {"completed": False, "error": f"Token failed: {err}"}

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
                MpesaPaymentService.QUERY_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            data = response.json()

            if data.get("ResultCode") == "0":
                return {"completed": True}
            elif data.get("ResultCode"):
                return {"completed": False, "failed": True}

            return {"completed": False}
        except Exception as e:
            return {"completed": False, "error": str(e)}

    @staticmethod
    def upgrade_user_subscription(uid, tier_name):
        try:
            expiry_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

            db.collection("users").document(uid).update({
                "subscription.tier": tier_name,
                "subscription.start_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "subscription.expiry_date": expiry_date
            })
            return {"success": True}
        except Exception as e:
            print(f"Error upgrading subscription: {e}")
            return {"success": False, "error": str(e)}