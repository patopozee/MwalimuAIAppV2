import random
import streamlit as st
import requests
from firebase_admin import auth
from services.firebase_init import db
from datetime import datetime
from services.email_service import send_email_code
from firebase_admin import firestore

db = firestore.client()

class MwalimuAuthService:
    @staticmethod
    def register_user(email, password, name, grade, age, tier="Free"):
        code = str(random.randint(100000, 999999))
        
        # Use email as document ID
        db.collection("pending_verifications").document(email).set({
            "code": code,
            "created_at": datetime.utcnow(),
            "user_data": {
                "name": name,
                "email": email,
                "password": password,
                "grade": grade,
                "age": age,
                "tier": "free"
            }
        })
        
        send_email_code(email, code)
        return {"success": True}

    @staticmethod
    def finalize_registration(email, entered_code):
        doc_ref = db.collection("pending_verifications").document(email)
        doc = doc_ref.get()
        
        # 1. Validate the code
        if not doc.exists or doc.get("code") != entered_code:
            return {"success": False, "error": "Invalid or expired verification code."}
        
        # 2. Extract data safely
        user_data = doc.get("user_data")
        
        # 3. Create the user with error handling
        try:
            user = auth.create_user(
                email=email, 
                password=user_data['password'], 
                display_name=user_data['name']
            )
        except auth.EmailAlreadyExistsError:
            return {"success": False, "error": "This email is already registered."}
        except Exception as e:
            return {"success": False, "error": f"Auth error: {str(e)}"}
        
        # 4. Save to 'users' collection
        try:
            db.collection("users").document(user.uid).set({
                "uid": user.uid,
                "name": user_data['name'],
                "email": user_data['email'],
                "grade": user_data['grade'],
                "age": user_data['age'],
                "tier": "Free",
                "created_at": datetime.utcnow().isoformat()
            })
            
            # 5. Cleanup
            doc_ref.delete()
            return {"success": True, "uid": user.uid}
        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}
    @staticmethod
    def login_user(email, password):
        try:
            user = auth.get_user_by_email(email)

            user_doc = db.collection("users").document(user.uid).get()

            if user_doc.exists:
                return {
                    "success": True,
                    "uid": user.uid,
                    "user_data": user_doc.to_dict()
                }

            return {
                "success": False,
                "error": "Student profile not found."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def send_password_reset_email(email):


        if "FIREBASE_WEB_API_KEY" not in st.secrets:
            return {"success": False, "error": "FIREBASE_WEB_API_KEY missing"}

        api_key = st.secrets["FIREBASE_WEB_API_KEY"]

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"

        payload = {
            "requestType": "PASSWORD_RESET",
            "email": email
        }

        try:
            response = requests.post(url, json=payload)

            if response.status_code == 200:
                return {"success": True}

            return {
                "success": False,
                "error": response.json()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}