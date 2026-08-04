import base64
import os
import streamlit as st
from styles.header import load


def render():
    load()

    logo = "assets/logo112.png"
    logo64 = ""

    if os.path.exists(logo):
        with open(logo, "rb") as f:
            logo64 = base64.b64encode(f.read()).decode()

    student = st.session_state.get("student_name", "Student")
    grade = st.session_state.get("student_grade", "Grade 6")
    subject = st.session_state.get("active_subject", "Mathematics")
    topic = st.session_state.get("active_topic", "Numbers")
    subtopic = st.session_state.get("active_sub_topic", "Place Value")
    tier = st.session_state.get("subscription_tier", "FREE")

    initial = student[0].upper() if student else "S"

    st.html(
        f"""
    <div class="mwalimu-header-wrapper">
        <div class="hdr-banner">
            <div class="hdr-left">
                <img class="hdr-logo" src="data:image/png;base64,{logo64}">
                <div class="hdr-title">
                    <h2>Mwalimu AI App</h2>
                    <span>Shaping Minds. Shifting Futures.</span>
                </div>
            </div>

            <div class="hdr-center">
                <span>{grade}</span> • <span>{subject}</span> • <span>{topic}</span> • <span>{subtopic}</span>
            </div>

            <div class="hdr-right">
                <div class="hdr-icon">🔔</div>
                <div class="hdr-icon">🌙</div>
                <div class="hdr-premium">{tier}</div>
                <div class="hdr-profile">
                    <div class="hdr-avatar">{initial}</div>
                    <div class="hdr-name">{student}</div>
                </div>
            </div>
        </div>
    </div>
    """
    )