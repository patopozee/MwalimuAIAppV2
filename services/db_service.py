import streamlit as st
import json
from datetime import datetime
from google.oauth2 import service_account
from google.cloud import firestore

class MwalimuDBService:
    # 1. Initialize the connection once and store it as a class attribute
    _credentials_dict = json.loads(st.secrets["firebase"]["service_account_json"])
    _creds = service_account.Credentials.from_service_account_info(_credentials_dict)
    db = firestore.Client(credentials=_creds, project=_credentials_dict["project_id"])

    @staticmethod
    def save_quiz_result(uid, topic, score, total_questions):
        result_ref = MwalimuDBService.db.collection("users").document(uid).collection("quiz_results").document()
        result_ref.set({
            "topic": topic,
            "score": score,
            "total_questions": total_questions,
            "percentage": int((score / total_questions) * 100),
            "timestamp": datetime.utcnow().isoformat()
        })

    @staticmethod
    def log_interaction(uid, action_type):
        # Force cache invalidation since user stats just changed
        st.cache_data.clear()
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_ref = MwalimuDBService.db.collection("users").document(uid).collection("usage_logs").document(today)
        
        doc = log_ref.get()
        if doc.exists:
            current_count = doc.to_dict().get(action_type, 0)
            log_ref.update({action_type: current_count + 1})
        else:
            log_ref.set({action_type: 1, "date": today})

    @staticmethod
    @st.cache_data(ttl=10, show_spinner=False)  # 👈 CACHES NETWORK READ FOR 10 SECONDS
    def get_daily_usage(uid, action_type):
        """
        Pulls usage data from Firestore on the first run, then serves it 
        from server RAM instantly on subsequent rapid clicks.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        doc = MwalimuDBService.db.collection("users").document(uid).collection("usage_logs").document(today).get()
        if doc.exists:
            return doc.to_dict().get(action_type, 0)
        return 0

    @staticmethod
    def increment_usage(uid, action_type):
        """
        Increments usage and immediately clears memory cache to ensure data precision.
        """
        # 👈 PURGES MEMORY COPIES INSTANTLY SO COUNTS REMAIN PRECISE
        st.cache_data.clear()
        
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_ref = MwalimuDBService.db.collection("users").document(uid).collection("usage_logs").document(today)
        
        # Atomically increment in the usage_logs document
        log_ref.set({
            action_type: firestore.Increment(1),
            "date": today
        }, merge=True)
