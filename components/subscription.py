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
        status_icon = ""

        # Common SVG design parameters ensuring vertical alignment
        svg_base = "style='width:16px; height:16px; vertical-align:middle; margin-right:4px; fill:{color};'"

        if expiry_date and str(tier).strip().lower() != "free":
            try:
                # Convert string to timezone-aware datetime for flawless comparison
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d").replace(tzinfo=UTC)
                remaining_days = (expiry - today).days

                if remaining_days > 0:
                    status_color = "#22C55E"
                    status_text = f"{remaining_days} days remaining"
                    # Hourglass Top SVG (Offline)
                    status_icon = f"<svg xmlns='http://w3.org' viewBox='0 -960 960 960' {svg_base.format(color=status_color)}><path d='m300-800 360 1v120L480-500 300-679v-121Zm0 600h360v120H300v-120Zm0-180h360v60H300v-60Zm180-80 180-180v-60H300v60l180 180Z'/></svg>"

                elif remaining_days == 0:
                    status_color = "#F59E0B"
                    status_text = "Expires today"
                    # Alarm Clock SVG (Offline)
                    status_icon = f"<svg xmlns='http://w3.org' viewBox='0 -960 960 960' {svg_base.format(color=status_color)}><path d='M480-80q-125 0-212.5-87.5T180-380q0-125 87.5-212.5T480-680q125 0 212.5 87.5T780-380q0 125-87.5 212.5T480-80Zm0-60q100 0 170-70t70-170q0-100-70-170t-170-70q-100 0-170 70t-70 170q0 100 70 170t170 70Zm0-180q13 0 21.5-8.5T510-350v-130q0-13-8.5-21.5T480-510q-13 0-21.5 8.5T450-480v130q0 13 8.5 21.5T480-320Z'/></svg>"

                else:
                    status_color = "#EF4444"
                    status_text = "Subscription expired"
                    # Block / Cancel SVG (Offline)
                    status_icon = f"<svg xmlns='http://w3.org' viewBox='0 -960 960 960' {svg_base.format(color=status_color)}><path d='M480-80q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T209-763q54-54 127-85.5T492-880q83 0 156 31.5T775-763q54 54 85.5 127T892-480q0 83-31.5 156T775-197q-54 54-127 85.5T480-80Zm0-60q142 0 241-99t99-241q0-59-19.5-112.5T546-686L274-214q53 35.5 106.5 54.5T480-140Zm-266-134 272-472q-53-35.5-106.5-54.5T220-820q-142 0-241 99t-99 241q0 59 19.5 112.5T214-274Z'/></svg>"

            except Exception:
                status_color = "#94A3B8"
                status_text = "Unable to determine expiry."
                status_icon = ""

        elif str(tier).strip().lower() == "free":
            status_color = "#3B82F6"
            status_text = "Upgrade to unlock Premium features"
            # Rocket SVG (Offline)
            status_icon = f"<svg xmlns='http://w3.org' viewBox='0 -960 960 960' {svg_base.format(color=status_color)}><path d='M760-760q-48 48-76 109.5T656-524L468-336q-16 16-36.5 24.5T390-303l-72 8q-23 2-38.5-13.5T265-347l9-72q3-21 11-41.5t25-36.5l188-188q24-24 55.5-38.5T619-738q64-4 125-32.5T760-760ZM328-261l39-4 163-163-35-35-163 163-4 39 23 23Z'/></svg>"

        # Render HTML string with safely embedded local vector shapes
        st.sidebar.markdown(
            f'''
            <div style="background: #101726; border: 1px solid rgba(59,130,246,0.15); border-radius: 14px; padding: 16px; margin-bottom: 12px;">
                <div style="font-size: 20px; color: #94A3B8; margin-bottom: 6px;">
                    Current Plan
                </div>
                <div style="font-size: 17px; font-weight: 700; color: white; margin-bottom: 10px;">
                    {tier}
                </div>
                <div style="color: {status_color}; font-size: 14px; font-weight: 600; display: flex; align-items: center;">
                    {status_icon} <span>{status_text}</span>
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

        # Import modal helper safely
        from services.upgrade_modal import upgrade_modal

        # Show upgrade prompt if user is on the Free tier
        if str(tier).strip().lower() == "free":
            # Swapped emoji out for native Material Icon token framework
            if st.sidebar.button(
                label="Upgrade to Premium", 
                icon=":material/rocket_launch:", 
                use_container_width=True
            ):
                upgrade_modal()
