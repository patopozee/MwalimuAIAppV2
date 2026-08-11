import streamlit as st
from datetime import datetime, UTC

from services.database import get_student_data


def render():

    
    if "user_email" in st.session_state:
        active_target_id = st.session_state.get("uid") or st.session_state.user_email
        
        # Safely fetch student data from database layer
        user_data = get_student_data(str(active_target_id))

        subscription = {}
        if user_data:
            subscription = user_data.get('subscription', {})
            tier = subscription.get('tier', 'Free')
        else:
            tier = 'Free'

        # Process dates cleanly using modern timezone-aware UTC objects
        today = datetime.now(UTC)
        expiry_date = subscription.get("expiry_date")

        status_text = ""
        status_color = "#22C55E"  # Default Green

        if expiry_date and str(tier).strip().lower() != "free":
            try:
                # Convert string to timezone-aware datetime for flawless comparison
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d").replace(tzinfo=UTC)
                remaining_days = (expiry - today).days

                if remaining_days > 0:
                    status_text = f"⏳ {remaining_days} days remaining"
                    status_color = "#22C55E"

                elif remaining_days == 0:
                    status_text = "⚠️ Expires today"
                    status_color = "#F59E0B"

                else:
                    status_text = "❌ Subscription expired"
                    status_color = "#EF4444"

            except Exception:
                status_text = "Unable to determine expiry."
                status_color = "#94A3B8"

        elif str(tier).strip().lower() == "free":
            status_text = "🚀 Upgrade to unlock Premium features"
            status_color = "#3B82F6"

        # --- FIX: Outer wrapper switched to single quotes (''') to isolate HTML double quotes ("") ---
        st.sidebar.markdown(
            f'''
            <div style="background: #101726; border: 1px solid rgba(59,130,246,0.15); border-radius: 14px; padding: 16px; margin-bottom: 12px;">
                <div style="font-size: 20px; color: #94A3B8; margin-bottom: 6px;">
                    Current Plan
                </div>
                <div style="font-size: 17px; font-weight: 700; color: white; margin-bottom: 10px;">
                    {tier}
                </div>
                <div style="color: {status_color}; font-size: 14px; font-weight: 600;">
                    {status_text}
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        # Import modal helper safely
        from services.upgrade_modal import upgrade_modal

        # Show upgrade prompt if user is on the Free tier
        if str(tier).strip().lower() == "free":
            if st.sidebar.button("🚀 Upgrade to Premium", use_container_width=True):
                st.session_state.show_upgrade_modal = True
                st.session_state.payment_status = "idle"  # Clear out stuck processing states
                st.rerun()


            #     #MOVED INSIDE SIDEBAR: Verification button for free users who just paid
            # if st.sidebar.button("💳 I've Paid, Check Status", use_container_width=True):
            #     # ----------------------------------------------------------------
            #     # TEMPORARY MOCK PAYMENT TRIGGER (REMOVE BEFORE PRODUCTION)
            #     # ----------------------------------------------------------------
            #     from datetime import datetime, timedelta
                
            #     mock_expiry = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
            #     mock_subscription = {
            #         "tier": "Premium",  # Change this to "Mwalimu AI Plus" to test that tier too
            #         "expiry_date": mock_expiry,
            #         "payment_status": "Completed",
            #         "reference_id": "MOCK_PAYMENT_12345"
            #     }
                
            #     # Directly update your Firestore user document layout
            #     from services.database import db
            #     uid = st.session_state.get("uid") or st.session_state.user_email
            #     db.collection('users').document(str(uid)).update({
            #         "subscription": mock_subscription
            #     })
            #     st.sidebar.success("🔧 Mock Payment Simulated!")
            #     # ----------------------------------------------------------------

            #     # Refresh data from database to check if everything updates live
            #     user_data = get_student_data(st.session_state.user_email)
            #     subscription = user_data.get('subscription', {}) if user_data else {}
            #     updated_tier = subscription.get('tier', 'Free')
                
            #     if str(updated_tier).strip().lower() != "free":
            #        st.sidebar.success(f"Upgrade successful! You are now {updated_tier}")
            #        st.rerun()
            #     # else:
            #     #    st.sidebar.warning("Payment not confirmed yet. Please wait a moment.")