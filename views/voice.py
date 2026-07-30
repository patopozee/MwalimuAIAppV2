import streamlit as st
from services.upgrade_modal import upgrade_modal
from voice_page import render_voice_tutor_page
import os
from services.upgrade_modal import upgrade_modal
from services.database import (
    
    get_student_data  #  ADD THIS LINE HERE
)
name = st.session_state.get("student_name", "")
grade = st.session_state.get("grade", "")
age = st.session_state.get("age", "")
student = st.session_state.get("student_name", "")

def render():   
    st.markdown("---")
        
    # 🚀 FIX: Read directly from session_state so it fetches the live data instantly!
    live_student_name = st.session_state.get("student_name", "").strip()
    
    if not live_student_name:
        st.warning("Please enter your name in the Student Profile registration section.")
    else:
        # 1. Fetch the latest user profile to get the tier
        user_data = get_student_data(st.session_state.uid)
        subscription = user_data.get('subscription', {}) if user_data else {}
        tier = subscription.get('tier', 'Free')

        # 2. GATE THE FEATURE: Only allow 'Premium' tier
        if str(tier).strip().lower() == "premium":
            # Check if environment setup exists
            api_key = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
            if api_key:
                # 🎯 FIX: Declare an explicit localized client inside this scope block!
                from openai import OpenAI
                local_voice_client = OpenAI(
                    base_url="https://openrouter.ai", 
                    api_key=api_key
                )
                
                # 🛡️ LOCAL HISTORY FORCING AT THE SWITCH ROUTER ENTRY
                # 🛡️ LOCAL HISTORY FORCING AT THE SWITCH ROUTER ENTRY
                current_subject = st.session_state.get("active_subject", "General Studies")

                if (
                    "voice_chat_history" not in st.session_state
                    or st.session_state.get("last_voice_subject") != current_subject
                ):

                    from services.database import get_voice_chat_history

                    try:
                        all_raw_history = get_voice_chat_history(
                            str(st.session_state.get("uid", "")),
                            current_subject
                        )

                        # Clear previous history
                        st.session_state.voice_chat_history = []

                        # Keep only voice records
                        voice_records = [
                            msg for msg in all_raw_history
                            if msg.get("is_voice") or msg.get("role") in ["voice_student", "voice_assistant"]
                        ]

                        # Convert roles for the UI
                        for msg in voice_records:

                            if msg["role"] in ["voice_student", "student", "user"]:
                                ui_role = "user"
                            else:
                                ui_role = "assistant"

                            st.session_state.voice_chat_history.append({
                                "role": ui_role,
                                "content": msg["content"],
                                "is_voice": True,
                                "audio_bytes": msg.get("audio_bytes")
                            })

                        # ✅ Only update after successful loading
                        st.session_state.last_voice_subject = current_subject

                    except Exception:
                        st.session_state.voice_chat_history = []
                # Pass this localized client directly to your voice tutor engine
                render_voice_tutor_page(local_voice_client)
            else:
                st.error("OpenRouter Gateway API configurations are currently offline.")
            
        else:
            # 3. Handle the blocked state
            st.warning("🎙️ **Voice Tutor Mode is a Premium Feature.**")
            st.info("Upgrade to Premium to unlock interactive audio learning and more!")
            if st.button("🚀 Upgrade to Premium", key="voice_upgrade"):
                upgrade_modal()