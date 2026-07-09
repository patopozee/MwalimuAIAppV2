import streamlit as st
from services.db_service import MwalimuDBService

# Business Rule Constraints Dictionary Mapping
TIER_LIMITS = {
    "Free": {
        "questions": 1,
        "quizzes": 1,
        "flashcards": 1,
        "lessons": 1,
        "has_study_plan": 1,
        "has_voice": 1,
    },
    "Mwalimu AI Plus": {
        "questions": 50,
        "quizzes": 15,
        "flashcards": 50,
        "lessons": 1,
        "has_study_plan": 1,
        "has_voice": False
    },
    "Premium": {
        "questions": float('inf'),
        "quizzes": float('inf'),
        "flashcards": float('inf'),
        "lessons": float('inf'),
        "has_study_plan": float('inf'),
        "has_voice": True
    }
}

def verify_tier_allowance(uid, tier, action_type):
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["Free"])
    max_allowance = limits.get(action_type, 0)
    
    current_usage = MwalimuDBService.get_daily_usage(uid, action_type)
    
    # Debug print BEFORE the logic so you always see what's happening
    print(f"DEBUG: UID={uid}, Tier={tier}, Action={action_type}, Usage={current_usage}, Limit={max_allowance}")
    
    # 1. If max_allowance is 0 or False, they have no allowance
    if max_allowance == 0 or max_allowance is False:
        return False
        
    # 2. Check usage (if not infinite)
    # Only block if usage is strictly GREATER than or EQUAL to the limit
    if max_allowance != float('inf') and current_usage >= max_allowance:
        return False
        
    # 3. If we passed all checks, they are allowed
    return True
