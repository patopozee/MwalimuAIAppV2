import streamlit as st
from services.db_service import MwalimuDBService

# Business Rule Constraints Dictionary Mapping
TIER_LIMITS = {
    "Free": {
        "questions": 1,
        "quizzes": 5,
        "flashcards": 20,
        "has_study_plan": False,
        "has_voice": False
    },
    "Mwalimu AI Plus": {
        "questions": 50,
        "quizzes": 15,
        "flashcards": 50,
        "has_study_plan": True,
        "has_voice": False
    },
    "Premium": {
        "questions": float('inf'),
        "quizzes": float('inf'),
        "flashcards": float('inf'),
        "has_study_plan": True,
        "has_voice": True
    }
}

def verify_tier_allowance(uid, tier, action_type):
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["Free"])
    current_usage = MwalimuDBService.get_daily_usage(uid, action_type)
    max_allowance = limits.get(action_type, 0)
    
    
    if max_allowance != float('inf') and current_usage >= max_allowance:
        return False
    return True