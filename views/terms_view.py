import streamlit as st
from services.legal_text import TERMS_AND_CONDITIONS

def render_terms_and_conditions_view():
    st.markdown("## 📜 Platform Terms of Service & Privacy Statement")
    st.caption("Kenya Competency-Based Curriculum (CBC) Platform Compliance Engine")
    st.markdown("---")

    # Render inside a scrollable container for desktop and mobile devices
    with st.container(border=True):
        st.markdown(TERMS_AND_CONDITIONS)

    st.markdown("<br>", unsafe_allow_html=True)
    
    