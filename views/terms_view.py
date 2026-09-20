import streamlit as st
from services.legal_text import TERMS_AND_CONDITIONS

def render_terms_and_conditions_view():
    # Replaced the emoji with a custom colored native Material Icon token
    st.markdown(
        '## <span style="color: #2473F2;">:material/gavel:</span> Platform Terms of Service & Privacy Statement', 
        unsafe_allow_html=True
    )

    st.caption("Kenya Competency-Based Curriculum (CBC) Platform Compliance Engine")
    st.markdown("---")

    # Render inside a scrollable container for desktop and mobile devices
    with st.container(border=True):
        st.markdown(TERMS_AND_CONDITIONS)

    st.markdown("<br>", unsafe_allow_html=True)
    
    