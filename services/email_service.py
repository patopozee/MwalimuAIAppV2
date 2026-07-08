import sib_api_v3_sdk
import streamlit as st


def send_email_code(to_email, code):

    configuration = sib_api_v3_sdk.Configuration()

    configuration.api_key["api-key"] = st.secrets["BREVO_API_KEY"]

    api = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    email = sib_api_v3_sdk.SendSmtpEmail(

        sender={
            "email": st.secrets["BREVO_SENDER_EMAIL"],
            "name": st.secrets["BREVO_SENDER_NAME"]
        },

        to=[{"email": to_email}],

        subject="Verify your Mwalimu AI account",

        html_content=f"""
        <h2>Welcome to Mwalimu AI 👋</h2>

        <p>Your verification code is:</p>

        <h1 style="font-size:40px;color:#2563eb;">{code}</h1>

        <p>This code expires in <b>10 minutes</b>.</p>

        <p>If you didn't request this code, simply ignore this email.</p>

        <hr>

        <small>Mwalimu AI Team</small>
        """
    )

    try:
        api.send_transac_email(email)
        return True

    except Exception as e:
        print("Brevo Error:", e)
        return False