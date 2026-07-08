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

@st.dialog(" ")
def show_upgrade_modal():

    logo = Image.open("assets/mpesa_logo.png")

    # ---------- Logo ----------
    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.image("assets/mpesa_logo.png", width="stretch")

    st.markdown(
        "<h2 style='text-align:center;margin-bottom:0;'>Upgrade to Premium</h2>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center;color:#9CA3AF;font-size:15px;'>"
        "Unlock unlimited learning with <b>Mwalimu AI Premium</b>"
        "</p>",
        unsafe_allow_html=True
    )

    st.divider()

    # ---------- Phone ----------
    phone = st.text_input(
        "📱 Enter M-Pesa Phone Number",
        placeholder="2547XXXXXXXX"
    )

    st.write("")

    # ---------- Compact Card ----------
    with st.container(border=True):

        left, right = st.columns(2)

        with left:
            st.caption("💰 Amount")
            st.markdown(
                "<h2 style='color:#22c55e;margin-top:0;'>KES 500</h2>",
                unsafe_allow_html=True
            )

        with right:
            st.caption("🛡 Payment")
            st.markdown(
                "<h4 style='margin-top:8px;'>STK Push</h4>",
                unsafe_allow_html=True
            )

        st.divider()

        st.success("✔ Secure • Instant • Encrypted")

    st.write("")

    # ---------- Pay ----------
    if st.button("Pay 500 KES", width="stretch"):

        phone = phone.strip()

        if not phone.startswith("254"):
            st.error("Phone number must start with 254.")
            return

        if len(phone) != 12:
            st.error("Use format: 2547XXXXXXXX")
            return

        with st.spinner("Sending STK Push..."):

            result = MpesaPaymentService.initiate_stk_push(
                phone_number=phone,
                amount=500,
                uid=st.session_state.user_email
            )

            if result["success"]:
                st.success("✅ STK Push sent to your phone.")
                st.balloons()

            else:
                st.error(result["message"])

    st.markdown(
        "<p style='text-align:center;color:#9CA3AF;font-size:13px;'>"
        "You will receive an M-Pesa prompt on your phone."
        "</p>",
        unsafe_allow_html=True
    )