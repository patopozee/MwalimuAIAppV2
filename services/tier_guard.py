import streamlit as st
from services.db_service import MwalimuDBService
from datetime import datetime
from services.database import get_student_data

# Business Rule Constraints Dictionary Mapping
TIER_LIMITS = {
    "Free": {
        "questions": 15,
        "quizzes": 5,
        "flashcards": 5,
        "lessons": 1,
        "has_study_plan": 1,
        "has_upload" : 0,
        "has_voice": 0,
    },
    "Mwalimu AI Plus": {
        "questions": 50,
        "quizzes": 15,
        "flashcards": 30,
        "lessons": 5,
        "has_study_plan": 5,
        "has_voice": 10,
        "has_voice": False
    },
    "Premium": {
        "questions": float('inf'),
        "quizzes": float('inf'),
        "flashcards": float('inf'),
        "lessons": float('inf'),
        "has_study_plan": float('inf'),
        "has_upload": float('inf'),
        "has_voice": True
    }
}

def is_subscription_active(user_data):
    if user_data is None:
        return False
        
    subscription = user_data.get("subscription", {})
    expiry = subscription.get("expiry_date")
    
    if not expiry: 
        return False
        
    # Standard UTC day comparison pattern matching 
    if datetime.utcnow().strftime("%Y-%m-%d") > expiry:
        return False
    return True

def verify_tier_allowance(uid, tier, action_type):
    # 1. Standardize and clean up the incoming tier string input context
    raw_tier_str = str(tier).strip().lower()
    
    if "premium" in raw_tier_str:
        active_tier = "Premium"
    elif "plus" in raw_tier_str:
        active_tier = "Mwalimu AI Plus"
    else:
        active_tier = "Free"

    # 2. Extract standard limits from our strict dictionary schema lookup
    limits = TIER_LIMITS.get(active_tier, TIER_LIMITS["Free"])
    
    max_allowance = limits.get(action_type, 0)
    current_usage = MwalimuDBService.get_daily_usage(uid, action_type)
    
    # 3. PRINT DIAGNOSTIC METRICS TO CONSOLE FOR TRACKING
    #print(f"DEBUG_FIXED: Active_Tier_Mapped={active_tier}, Action={action_type}, Usage={current_usage}, Limit={max_allowance}")
    
    # 4. Enforce our dynamic structural guard logic checks
    if max_allowance == 0 or max_allowance is False:
        return False
        
    if max_allowance != float('inf') and current_usage >= max_allowance:
        return False
        
    return True
