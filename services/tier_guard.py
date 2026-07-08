import streamlit as st
from services.db_service import MwalimuDBService

# Business Rule Constraints Dictionary Mapping
TIER_LIMITS = {
    "Free": {
        "questions": 1,
        "quizzes": 5,
        "flashcards": 20,
        "has_study_plan": 0,
        "has_voice": False
    },
    "Mwalimu AI Plus": {
        "questions": 50,
        "quizzes": 15,
        "flashcards": 50,
        "has_study_plan": 1,
        "has_voice": False
    },
    "Premium": {
        "questions": float('inf'),
        "quizzes": float('inf'),
        "flashcards": float('inf'),
        "has_study_plan": float('inf'),
        "has_voice": True
    }
}

def verify_tier_allowance(uid, tier, action_type):
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["Free"])
    max_allowance = limits.get(action_type, 0)
    
    current_usage = MwalimuDBService.get_daily_usage(uid, action_type)
    
    # If max_allowance is 0 or False, they have no allowance
    if max_allowance == 0 or max_allowance is False:
        return False
        
    if max_allowance != float('inf') and current_usage >= max_allowance:
        return False
    
    print(f"DEBUG: UID={uid}, Tier={tier}, Action={action_type}, Usage={current_usage}, Limit={max_allowance}")

    if max_allowance != float('inf') and current_usage >= max_allowance:
        return False
    return True
