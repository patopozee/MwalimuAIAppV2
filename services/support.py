import requests
import streamlit as st


BREVO_API_KEY = st.secrets["BREVO_API_KEY"]


def send_support_email(name, email, phone, subject, message):

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    body = {
        "sender": {
            "name": "Mwalimu AI Support",
            "email": "info@mwalimuaiapp.com"
        },

        "to": [
            {
                "email": "info@mwalimuaiapp.com",
                "name": "Support Desk"
            }
        ],

        "replyTo": {
            "email": email,
            "name": name
        },

        "subject": f"Website Contact: {subject}",

        "htmlContent": f"""
        <h2>New Contact Form Submission</h2>

        <p><b>Name:</b> {name}</p>

        <p><b>Email:</b> {email}</p>

        <p><b>Phone:</b> {phone}</p>

        <p><b>Subject:</b> {subject}</p>

        <hr>

        <p>{message}</p>
        """
    }

    response = requests.post(url, headers=headers, json=body)

    return response.status_code == 201