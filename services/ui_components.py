from PIL import Image
import streamlit as st
from services.payment_service import MpesaPaymentService

st.markdown("""
    <style>

    /* Smaller centered dialog */
    [data-testid="stDialog"] > div {
        width: 430px !important;
        max-width: 430px !important;
        border-radius: 18px !important;
        padding: 0.8rem 1.1rem !important;
    }

    /* Smaller buttons */
    div.stButton > button {
        height: 48px !important;
        border-radius: 12px !important;
        font-size: 17px !important;
        font-weight: 600 !important;
    }

    /* Reduce top spacing inside dialog */
    [data-testid="stDialog"] h1,
    [data-testid="stDialog"] h2,
    [data-testid="stDialog"] h3 {
        margin-top: 0rem !important;
        margin-bottom: .3rem !important;
    }

    </style>
    """, unsafe_allow_html=True)

@st.dialog("Upgrade to Premium")
def show_upgrade_modal():
    # 1. Cleaner Header Section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/mpesa_logo.png") # Streamlit handles width well automatically
    
    st.markdown("<h2 style='text-align:center;'>Upgrade to Premium</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#6B7280;'>Unlock unlimited learning with <b>Mwalimu AI Premium</b></p>", unsafe_allow_html=True)

    # 2. Compact Pricing Card
    with st.container(border=True):
        # Use columns for a grid-like alignment
        c1, c2 = st.columns([1, 1])
        with c1:
            st.caption("Amount")
            st.subheader("KES 999")
        with c2:
            st.caption("Payment Method")
            st.write("M-Pesa STK Push")
        
        st.divider()
        st.caption("✔ Secure • Instant • Encrypted")

    # 3. Input Section
    phone = st.text_input("Enter M-Pesa Phone Number", placeholder="2547XXXXXXXX")

    # 4. Action Button
    if st.button("Pay 999 KES", type="primary", use_container_width=True):
        phone = phone.strip()
        if not phone.startswith("254") or len(phone) != 12:
            st.error("Please enter a valid M-Pesa number (e.g., 2547XXXXXXXX)")
        else:
            with st.spinner("Sending STK Push..."):
                result = MpesaPaymentService.initiate_stk_push(
                    phone_number=phone,
                    amount=500,
                    uid=st.session_state.user_email
                )
                if result["success"]:
                    st.success("✅ Check your phone for the M-Pesa prompt.")
                    st.balloons()
                else:
                    st.error(result.get("message", "Payment failed. Please try again."))

    st.caption("You will receive an M-Pesa prompt on your phone to complete the payment.", help="Ensure your phone is unlocked.")