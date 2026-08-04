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

    st.html(f"""
    <div class="mw-header">

        <div class="mw-brand-card">

            <img class="mw-logo"
            src="data:image/png;base64,{logo64}">

            <div class="mw-brand-text">

                <div class="mw-title">
                    Mwalimu AI
                </div>

                <div class="mw-subtitle">
                    Shaping Minds. Shifting Futures.
                </div>

            </div>

        </div>

        <div class="mw-context-card">

            <span>{grade}</span>

            <span>•</span>

            <span>{subject}</span>

            <span>•</span>

            <span>{topic}</span>

            <span>•</span>

            <span>{subtopic}</span>

        </div>

        <div class="mw-right">

            <div class="mw-icon">🔔</div>

            <div class="mw-icon">🌙</div>

            <div class="mw-plan">

                {tier}

            </div>

            <div class="mw-profile">

                <div class="mw-avatar">

                    {initial}

                </div>

                <div class="mw-name">

                    {student}

                </div>

            </div>

        </div>

    </div>
    """)