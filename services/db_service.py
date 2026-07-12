import os
import json
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from google.cloud import firestore

class MwalimuDBService:
    # 1. Flexible initialization: Check for environment variable, fallback to st.secrets
    _json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    
    if not _json_str:
        # Fallback for local development if running via 'streamlit run'
        _json_str = json.dumps(st.secrets["firebase"]["service_account_json"])
    
    _credentials_dict = json.loads(_json_str)
    _creds = service_account.Credentials.from_service_account_info(_credentials_dict)
    db = firestore.Client(credentials=_creds, project=_credentials_dict["project_id"])

    @staticmethod
    def save_quiz_result(uid, topic, score, total_questions):
        # Use MwalimuDBService.db
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
        # Use MwalimuDBService.db
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_ref = MwalimuDBService.db.collection("users").document(uid).collection("usage_logs").document(today)
        
        doc = log_ref.get()
        if doc.exists:
            current_count = doc.to_dict().get(action_type, 0)
            log_ref.update({action_type: current_count + 1})
        else:
            log_ref.set({action_type: 1, "date": today})

    @staticmethod
    def get_daily_usage(uid, action_type):
        # Use MwalimuDBService.db
        today = datetime.utcnow().strftime("%Y-%m-%d")
        doc = MwalimuDBService.db.collection("users").document(uid).collection("usage_logs").document(today).get()
        if doc.exists:
            return doc.to_dict().get(action_type, 0)
        return 0

    @staticmethod
    def increment_usage(uid, action_type):
        """
        Increments usage in the SAME collection used by get_daily_usage.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        # Use the exact same path as get_daily_usage
        log_ref = MwalimuDBService.db.collection("users").document(uid).collection("usage_logs").document(today)
        
        # Atomically increment in the usage_logs document
        log_ref.set({
            action_type: firestore.Increment(1),
            "date": today
        }, merge=True)