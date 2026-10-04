import time
import streamlit as st
from PIL import Image
from services.payment_service import MpesaPaymentService


@st.dialog("Upgrade your account")
def upgrade_modal():
    st.markdown("""
    <style>

    /* ===============================
        Ultra-Compact 2-Plan Upgrade Modal
    ================================ */
    [data-testid="stDialog"] > div{
        width:700px !important;
        max-width:700px !important;
        border-radius:16px !important;
        padding:0.5rem 0.8rem !important;
    }

    /* Minimal header margins */
    [data-testid="stDialog"] h2{
        margin-top:0rem !important;
        margin-bottom:0rem !important;
        font-size:1.15rem !important;
    }

    [data-testid="stDialog"] p{
        margin-bottom:0.15rem !important;
        font-size:0.75rem !important;
    }

    /* Close gap between columns */
    [data-testid="stHorizontalBlock"]{
        gap:0.4rem !important;
    }

    /* Slim plan containers */
    [data-testid="stVerticalBlockBorderWrapper"]{
        border-radius:10px !important;
        padding:0.3rem 0.4rem !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"] h3 {
        font-size:0.9rem !important;
        margin-bottom:0rem !important;
    }

    /* Tiny buttons */
    div.stButton > button{
        height:28px !important;
        border-radius:6px !important;
        font-size:12px !important;
        font-weight:600 !important;
        padding:0px !important;
    }

    /* Input field */
    div[data-baseweb="input"]{
        border-radius:6px !important;
    }

    /* Divider spacing */
    hr{
        margin:0.3rem 0 !important;
    }

    /* Tight feature lists */
    ul{
        margin-top:0.05rem !important;
        margin-bottom:0.05rem !important;
        padding-left:0.6rem !important;
    }

    li{
        margin-bottom:0.05rem !important;
        font-size:10.5px !important;
        line-height:1.15 !important;
    }

    /* Logo constraint */
    img{
        max-height: 28px !important;
        margin-bottom:0rem !important;
    }

    </style>
    """, unsafe_allow_html=True)

    if "selected_plan" not in st.session_state:
        st.session_state.selected_plan = "plus"

    # -------------------------------------------------------
    # Header
    # -------------------------------------------------------
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        try:
            st.image("assets/mpesa_logo.png")
        except Exception:
            pass

    st.markdown(
        "<h2 style='text-align:center;'>Choose your plan</h2>",
        unsafe_allow_html=True
    )

    # -------------------------------------------------------
    # Two Plans (Plus & Premium Only)
    # -------------------------------------------------------
    col_plus, col_premium = st.columns(2)

    with col_plus:
        with st.container(border=True):
            st.subheader("🧠 Mwalimu AI Plus")
            st.write("**KES 499 / mo**")
            st.markdown("""
✓ 50 AI Questions / day  
✓ 15 Assessment Quizzes  
✓ 30 Flashcards / day  
✓ 5 CBC Lessons / day  
✓ 5 Study Plans / day  
✓ Learning Management  
""")
            if st.button("Choose Plus", key="choose_plus", use_container_width=True):
                st.session_state.selected_plan = "plus"

    with col_premium:
        with st.container(border=True):
            st.subheader("👑 Premium")
            st.write("**KES 999 / mo**")
            st.markdown("""
✓ Unlimited Prompts & Quizzes  
✓ Unlimited Flashcards  
✓ Full Voice Tutor Mode  
✓ Personalized Study Plans  
✓ Learning Management  
✓ Advanced Weak-Topics  
""")
            if st.button("Choose Premium", key="choose_premium", use_container_width=True):
                st.session_state.selected_plan = "premium"

    st.divider()

    # -------------------------------------------------------
    # Payment Section
    # -------------------------------------------------------
    if st.session_state.selected_plan == "plus":
        amount = 499
        plan_display = "Mwalimu AI Plus"
    else:
        amount = 999
        plan_display = "Mwalimu AI Premium"

    col_info, col_input = st.columns([1, 1.3])
    
    with col_info:
        st.markdown(f"**Selected:** {plan_display}")
        st.markdown(f"**Total:** KES {amount}")

    with col_input:
        phone = st.text_input(
            "M-Pesa Number",
            placeholder="2547XXXXXXXX",
            label_visibility="collapsed"
        )
    #-------------------------------------------------------
    # Ensure our check request tracker status is initialized safely in session state
    if "active_checkout_id" not in st.session_state:
        st.session_state.active_checkout_id = None

    if st.button(
        f"Pay KES {amount} via M-Pesa",
        type="primary",
        use_container_width=True
    ):
        # ------------------------------------------------------------------
        # 📲 SMART M-PESA NUMBER SANITIZER & FORMATTER
        # ------------------------------------------------------------------
        clean_phone = phone.strip().replace("+", "").replace("-", "").replace(" ", "")

        if clean_phone.startswith("0"):
            clean_phone = "254" + clean_phone[1:]
        elif clean_phone.startswith("7") or clean_phone.startswith("1"):
            if len(clean_phone) == 9:
                clean_phone = "254" + clean_phone

        if not clean_phone.startswith("254") or len(clean_phone) != 12 or not clean_phone.isdigit():
            st.error("⚠️ Invalid Number! Please enter a valid Safaricom phone number (e.g. 07XXXXXXXX or 01XXXXXXXX).")
            return

        phone = clean_phone

        # ------------------------------------------------------------------
        # INITIATE STK PUSH 
        # ------------------------------------------------------------------
        with st.spinner("Initiating payment request..."):
            try:
                result = MpesaPaymentService.initiate_stk_push(
                    phone_number=phone,
                    amount=int(amount),
                    uid=st.session_state.get("uid"),
                    plan=st.session_state.selected_plan  
                )
            except Exception as err:
                result = {"success": False, "message": f"Backend Error: {str(err)}"}

        if result.get("success"):
            st.session_state.active_checkout_id = result.get("checkout_request_id")
            checkout_request_id = st.session_state.active_checkout_id
            
            payment_successful = False
            
            # 🎯 THE CRITICAL FIX FOR PYLANCE: Pre-declare the variable structure
            status_result = {"completed": False, "failed": False}
            
            # The loop status indicator block
            with st.status("📲 STK Push sent! Waiting for M-Pesa PIN entry...", expanded=True) as status_box:
                for i in range(24):  # Check status over 120s
                    time.sleep(5)                    
                    
                    # Re-fetch the live status matching your database records inside the loop
                    status_result = MpesaPaymentService.check_transaction_status(checkout_request_id)
                    
                    if status_result.get("completed"):
                        payment_successful = True
                        status_box.update(label="✅ Payment confirmed!", state="complete", expanded=False)
                        break
                    elif status_result.get("failed"):
                        status_box.update(label="❌ Payment cancelled or failed. If paid, refresh Subscription Status then refresh the page", state="error", expanded=False)
                        break
                
                # Pylance is now guaranteed that status_result is bound here
                if not payment_successful and not status_result.get("completed") and not status_result.get("failed"):
                    status_box.update(label="⏱️ Payment pending verification...", state="running", expanded=False)

            if payment_successful:
                MpesaPaymentService.upgrade_user_subscription(
                    uid=st.session_state.get("uid"), 
                    tier_name=st.session_state.selected_plan  
                )
                st.success("✅ Payment successful! Account upgraded.")
                st.balloons()
                time.sleep(2)
                st.session_state.active_checkout_id = None 
                st.rerun()
            else:
                final_status = MpesaPaymentService.check_transaction_status(checkout_request_id)
                if final_status.get("failed"):
                    st.error("❌ Payment cancelled or failed.")
                else:
                    st.warning("⏱️ The request timed out on our screen, but it might still be processing on your phone. Click the refresh button below if you just finished entering your PIN.")
        else:
            err_msg = result.get("message") or result.get("errorMessage") or "Payment failed."
            st.error(f"Payment Failed. Check Your Phone for M-Pesa Prompt: {err_msg}")

    # ------------------------------------------------------------------
    # 🔄 FALLBACK OUT-OF-FLOW REFRESH BUTTON (Fixed Streamlit Button Bug)
    # ------------------------------------------------------------------
    # Placing this out here allows students to click refresh stably without losing state references!
    if st.session_state.active_checkout_id is not None:
        st.write("---")
        st.info("Entered your PIN but your account screen hasn't updated yet? Click below to check again.")
        if st.button("🔄 Refresh Subscription Status", use_container_width=True, key="fallback_manual_refresh_btn"):
            with st.spinner("Re-checking transaction status ledger logs..."):
                check_again = MpesaPaymentService.check_transaction_status(st.session_state.active_checkout_id)
                if check_again.get("completed"):
                    MpesaPaymentService.upgrade_user_subscription(
                        uid=st.session_state.get("uid"), 
                        tier_name=st.session_state.selected_plan  
                    )
                    st.success("✅ Payment confirmed! Account upgraded successfully.")
                    st.balloons()
                    time.sleep(2)
                    st.session_state.active_checkout_id = None # Clear state tracker reference
                    st.rerun()
                else:
                    st.error("Transaction not confirmed yet. Please verify your PIN entry or wait a few seconds before trying again.")

    st.caption("Subscription activates automatically upon successful payment.")
