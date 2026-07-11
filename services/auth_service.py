# services/auth_service.py
import random
import streamlit as st
import requests
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter

# ---------------------------------------------------------------------
# FIXED: Move Firebase Auth import to top level to avoid unbound exceptions
# ---------------------------------------------------------------------
from firebase_admin import auth
from services.database import db

class MwalimuAuthService:
    @staticmethod
    def register_user(email, password, name, grade, age, tier="Free"):
        code = str(random.randint(100000, 999999))
        db.collection("pending_verifications").document(email.strip().lower()).set({
            "code": code,
            "created_at": datetime.utcnow(),
            "user_data": {
                "name": name,
                "email": email,
                "password": password, # Held temporarily until verification finishes
                "grade": grade,
                "age": age,
                "tier": tier
            }
        })
        from services.email_service import send_email_code
        send_email_code(email.strip().lower(), code)
        return {"success": True}

    @staticmethod
    def finalize_registration(email, entered_code):
        doc_ref = db.collection("pending_verifications").document(email.strip().lower())
        doc = doc_ref.get()
        
        if not doc.exists or doc.get("code") != entered_code:
            return {"success": False, "error": "Invalid or expired verification code."}
            
        pending_data_raw = doc.get("user_data")
        pending_data = dict(pending_data_raw) if isinstance(pending_data_raw, dict) else {}
        
        try:
            # FIXED: auth is now fully bound and visible to the exception block below!
            user = auth.create_user(
                email=email.strip().lower(), 
                password=str(pending_data.get('password', '')), 
                display_name=str(pending_data.get('name', 'Student'))
            )
        except auth.EmailAlreadyExistsError:
            return {"success": False, "error": "This email is already registered."}
        except Exception as e:
            return {"success": False, "error": f"Auth creation failure: {str(e)}"}
            
        try:
            # Create public profile in Firestore cleanly WITHOUT storing a plaintext password!
            db.collection("users").document(user.uid).set({
                "uid": user.uid,
                "name": pending_data.get('name', 'Student'),
                "email": pending_data.get('email', email).strip().lower(),
                "grade": pending_data.get('grade', 'Grade 6'),
                "age": int(pending_data.get('age', 12)),
                "created_at": datetime.utcnow().isoformat(),
                "subscription": {
                    "tier": pending_data.get('tier', 'Free'),
                    "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "expiry_date": None
                }
            })
            doc_ref.delete()
            return {"success": True, "uid": user.uid}
        except Exception as e:
            return {"success": False, "error": f"Database initialization failure: {str(e)}"}

    @staticmethod
    def login_user(email, password):
        """
        SECURE PROD LOGIN: Authenticates directly using official Firebase identity paths.
        Omit manual plaintext database password checking to allow real logins.
        """
        if "FIREBASE_WEB_API_KEY" not in st.secrets:
            return {"success": False, "error": "FIREBASE_WEB_API_KEY missing from secrets."}
            
        api_key = str(st.secrets["FIREBASE_WEB_API_KEY"]).strip().strip('"').strip("'")
        
        
        # FIXED: Absolute target endpoint path prevents 404 connection rejections
        url = (
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        )
    
        payload = {
            "email": email.strip().lower(),
            "password": password,
            "returnSecureToken": True
        }
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers)
            res_json = response.json()
            
            if response.status_code == 200:
                local_id = res_json.get("localId") # Secure generated UID token
               

                user_doc = db.collection("users").document(local_id).get()

                              
                # Fetch accompanying profile parameters from Firestore using document UI
                user_doc = db.collection("users").document(local_id).get()

                
                if user_doc.exists:
                    
                    return {"success": True, "uid": local_id, "user_data": user_doc.to_dict()}

                # Fallback email matching lookup query
                query = db.collection("users").where(filter=FieldFilter("email", "==", email.strip().lower())).stream()
                for doc in query:
                    
                    return {"success": True, "uid": doc.id, "user_data": doc.to_dict()}
                return {"success": False, "error": "Profile details missing in database data stores."}
            else:
                
                error_msg = res_json.get("error", {}).get("message", "INVALID_LOGIN_CREDENTIALS")
                if error_msg in ["INVALID_PASSWORD", "EMAIL_NOT_FOUND", "INVALID_LOGIN_CREDENTIALS"]:
                    return {"success": False, "error": "Incorrect email or password."}
                return {"success": False, "error": f"Authentication rejected: {error_msg}"}
                
        except Exception as e:
            
            return {"success": False, "error": "Incorrect email or password."}

    @staticmethod
    def send_password_reset_email(email):
        """
        PRODUCTION RESET LINK DISPATCHER: Fires links securely via Google REST APIs.
        """
        

        if "FIREBASE_WEB_API_KEY" not in st.secrets:
            return {"success": False, "error": "FIREBASE_WEB_API_KEY missing from secrets."}
            
        api_key = str(st.secrets["FIREBASE_WEB_API_KEY"]).strip().strip('"').strip("'")
        url = (
            f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
        )
       
        payload = {
            "requestType": "PASSWORD_RESET",
            "email": email.strip().lower()
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
