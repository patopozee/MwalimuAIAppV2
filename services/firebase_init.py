import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json


@st.cache_resource
def initialize_firebase():
    """Initializes the production Firebase Admin SDK securely using secrets."""
    if not firebase_admin._apps:
        try:
            raw_json_str = st.secrets["Firebase"]["service_account_json"]
            cred_dict = json.loads(raw_json_str)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"❌ Failed to parse Firebase configuration: {e}")
            raise e
            
    return firestore.client()

db = initialize_firebase()
