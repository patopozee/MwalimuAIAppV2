from datetime import UTC, datetime
import streamlit as st
from services.database import db, get_student_data


from datetime import UTC, datetime
import streamlit as st

from services.database import db, get_student_data


def enforce_subscription_expiry(uid):
    """Check and enforce subscription expiry for the current user."""

    if not uid:
        return "Free"

    uid = str(uid)

    # ---------------------------------------------------------
    # Already checked during this Streamlit session
    # ---------------------------------------------------------
    cache_key = f"expiry_checked_{uid}"
    tier_key = f"user_tier_{uid}"

    if st.session_state.get(cache_key, False):
        return st.session_state.get(tier_key, "Free")

    try:
        # -----------------------------------------------------
        # Fetch current Firestore profile
        # -----------------------------------------------------
        user_data = get_student_data(uid)

        if not user_data:
            st.session_state[cache_key] = True
            st.session_state[tier_key] = "Free"
            return "Free"

        subscription = user_data.get("subscription") or {}

        tier = str(
            subscription.get("tier", "Free")
        ).strip()

        # -----------------------------------------------------
        # Already Free
        # -----------------------------------------------------
        if tier.lower() == "free":
            st.session_state[cache_key] = True
            st.session_state[tier_key] = "Free"
            return "Free"

        # -----------------------------------------------------
        # Paid subscription with no expiry date
        # -----------------------------------------------------
        expiry_date = subscription.get("expiry_date")

        if not expiry_date:
            st.session_state[cache_key] = True
            st.session_state[tier_key] = tier
            return tier

        # -----------------------------------------------------
        # Parse expiry date
        # -----------------------------------------------------
        expiry = datetime.strptime(
            str(expiry_date),
            "%Y-%m-%d"
        ).date()

        today = datetime.now(UTC).date()

        # -----------------------------------------------------
        # Still active
        # -----------------------------------------------------
        if today <= expiry:
            st.session_state[cache_key] = True
            st.session_state[tier_key] = tier
            return tier

        # =====================================================
        # EXPIRED → DOWNGRADE FIRESTORE
        # =====================================================

        db.collection("users").document(uid).update({
            "subscription.tier": "free",
            "subscription.payment_status": "Expired",
            "subscription.updated_at": datetime.now(UTC).isoformat(),
        })


        # -----------------------------------------------------
        # Clear cached database result if applicable
        # -----------------------------------------------------
        if hasattr(get_student_data, "clear"):
            get_student_data.clear()

        # -----------------------------------------------------
        # Store result so this session doesn't repeat the write
        # -----------------------------------------------------
        st.session_state[cache_key] = True
        st.session_state[tier_key] = "Free"

        return "Free"

    except Exception as e:
        print(
            f"[SUBSCRIPTION] Expiry enforcement failed "
            f"for UID {uid}: {e}"
        )

        # IMPORTANT:
        # Don't silently tell the rest of the app that the user
        # is Free if the database check itself failed.
        return None


def render():
    if "user_email" in st.session_state:
        active_target_id = (
            st.session_state.get("uid") or st.session_state.user_email
        )

        # Safely fetch student data
        user_data = get_student_data(str(active_target_id))

        subscription = {}
        if user_data:
            subscription = user_data.get("subscription", {})
            tier = subscription.get("tier", "Free")
        else:
            tier = "Free"

        today = datetime.now(UTC)
        expiry_date = subscription.get("expiry_date")

        status_text = ""
        status_color = "#22C55E"  # Default Green

        if expiry_date and str(tier).strip().lower() != "free":
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d").replace(
                    tzinfo=UTC
                )
                remaining_days = (expiry - today).days

                if remaining_days > 0:
                    status_text = f"⏳ {remaining_days} days remaining"
                    status_color = "#22C55E"

                elif remaining_days == 0:
                    status_text = "⚠️ Expires today"
                    status_color = "#F59E0B"

                else:
                    # Rely on enforce_subscription_expiry() for DB writes; render display state here
                    status_text = "❌ Subscription expired"
                    status_color = "#EF4444"
                    tier = "Free"

            except Exception:
                status_text = "Unable to determine expiry."
                status_color = "#94A3B8"

        elif str(tier).strip().lower() == "free":
            status_text = "🚀 Upgrade to unlock Premium features"
            status_color = "#3B82F6"

        # Sidebar Display Container
        st.sidebar.markdown(
            f"""
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
            """,
            unsafe_allow_html=True,
        )

        from services.upgrade_modal import upgrade_modal

        # Show upgrade prompt if user is on Free tier
        if str(tier).strip().lower() == "free":
            if st.sidebar.button(
                "🚀 Upgrade to Premium", use_container_width=True
            ):
                st.session_state.show_upgrade_modal = True
                st.session_state.payment_status = "idle"
                st.rerun()