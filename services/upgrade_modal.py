from PIL import Image
import time
import streamlit as st
from services.payment_service import MpesaPaymentService

st.markdown("""
<style>

/* ===============================
    Ultra-Compact 2-Plan Upgrade Modal
================---------------- */
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
    height:24px !important;
    border-radius:6px !important;
    font-size:11px !important;
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


@st.dialog("Upgrade your account")
def show_upgrade_modal():

    if "selected_plan" not in st.session_state:
        st.session_state.selected_plan = "plus"

    # -------------------------------------------------------
    # Header
    # -------------------------------------------------------
    col1, col2, col3 = st.columns([2,1,2])
    with col2:
        st.image("assets/mpesa_logo.png")

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
            if st.button("Choose Plus", key="choose_plus", width="stretch"):
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
            if st.button("Choose Premium", key="choose_premium", width="stretch"):
                st.session_state.selected_plan = "premium"

    st.divider()

    # -------------------------------------------------------
    # Payment Section (Side-by-side to save height)
    # -------------------------------------------------------
    if st.session_state.selected_plan == "plus":
        amount = 499
        plan_name = "Mwalimu AI Plus"
    else:
        amount = 999
        plan_name = "Mwalimu AI Premium"

    col_info, col_input = st.columns([1, 1.3])
    
    with col_info:
        st.markdown(f"**Selected:** {plan_name}")
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

        with st.spinner("Sending STK Push..."):
            result = MpesaPaymentService.initiate_stk_push(
                phone_number=phone,
                amount=amount,
                uid=st.session_state.get("uid"),
                plan=st.session_state.selected_plan
            )
            
            if result["success"]:
                checkout_request_id = result.get("checkout_request_id")
                st.info("📲 STK Push sent! Please enter your M-Pesa PIN on your phone...")
                
                progress_bar = st.progress(0)
                payment_successful = False
                
                # Poll Safaricom status for up to 30 seconds
                # Change this loop range from 6 to 12
                for i in range(6):
                    time.sleep(5)
                    progress_bar.progress((i + 1) * 8)  # Adjust step size accordingly
                    
                    status_result = MpesaPaymentService.check_transaction_status(checkout_request_id)
                    if status_result.get("completed"):
                        payment_successful = True
                        break
                    elif status_result.get("failed"):
                        break
                        
                if payment_successful:
                    # Automatically update user subscription in Firebase
                    MpesaPaymentService.upgrade_user_subscription(
                        uid=st.session_state.get("uid"), 
                        tier_name=plan_name
                    )
                    st.success("✅ Payment successful! Account upgraded.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("⚠️Once you pay, Click the button bellow and refresh the page to activate:")
                    if st.button("🔄 Unlock Account", width="stretch"):
                        MpesaPaymentService.upgrade_user_subscription(
                            uid=st.session_state.get("uid"), 
                            tier_name=plan_name
                        )
                        st.success("✅ Account successfully upgraded!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error(result.get("message", "Payment failed."))

    st.caption("Subscription activates automatically upon successful payment.")