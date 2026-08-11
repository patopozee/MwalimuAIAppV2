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

    if st.button(
        f"Pay KES {amount} via M-Pesa",
        type="primary",
        use_container_width=True
    ):
        phone = phone.strip()

        if not phone.startswith("254") or len(phone) != 12:
            st.error("Enter a valid phone number (2547XXXXXXXX).")
            return

        with st.spinner("Initiating payment request..."):
            try:
                result = MpesaPaymentService.initiate_stk_push(
                    phone_number=phone,
                    amount=int(amount),
                    uid=st.session_state.get("uid"),
                    plan=st.session_state.selected_plan  # Sends "plus" or "premium"
                )
            except Exception as err:
                result = {"success": False, "message": f"Backend Error: {str(err)}"}

        if result.get("success"):
            checkout_request_id = result.get("checkout_request_id")
            status_result = MpesaPaymentService.check_transaction_status(checkout_request_id)
            payment_successful = False
            
            # Clean progress status container
            with st.status("📲 STK Push sent! Waiting for M-Pesa PIN entry...", expanded=True) as status_box:
                for i in range(12):  # Check status over 60s
                    time.sleep(5)                    
                    
                    if status_result.get("completed"):
                        payment_successful = True
                        status_box.update(label="✅ Payment confirmed!", state="complete", expanded=False)
                        break
                    elif status_result.get("failed"):
                        status_box.update(label="❌ Payment cancelled or failed.", state="error", expanded=False)
                        break
                
                if not payment_successful and not status_result.get("failed"):
                    status_box.update(label="⏱️ Payment pending verification...", state="running", expanded=False)

            if payment_successful:
                MpesaPaymentService.upgrade_user_subscription(
                    uid=st.session_state.get("uid"), 
                    tier_name=st.session_state.selected_plan  # STRICTLY "plus" OR "premium"
                )
                st.success("✅ Payment successful! Account upgraded.")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.info("Entered PIN but account not updated?")
                if st.button("🔄 Refresh Subscription Status", use_container_width=True):
                    check_again = MpesaPaymentService.check_transaction_status(checkout_request_id)
                    if check_again.get("completed"):
                        MpesaPaymentService.upgrade_user_subscription(
                            uid=st.session_state.get("uid"), 
                            tier_name=st.session_state.selected_plan  # STRICTLY "plus" OR "premium"
                        )
                        st.success("✅ Payment confirmed! Account upgraded.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Transaction not confirmed yet. Please verify your PIN entry.")
        else:
            err_msg = result.get("message") or result.get("errorMessage") or "Payment failed."
            st.error(f"❌ Payment Initialization Failed: {err_msg}")

    st.caption("Subscription activates automatically upon successful payment.")