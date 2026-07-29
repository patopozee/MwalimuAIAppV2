import streamlit as st

def section(title, icon="📚"):
    st.markdown(
        f"""
        <h3 style="
            margin-bottom:10px;
            border-left:4px solid #3B82F6;
            padding-left:10px;
        ">
        {icon} {title}
        </h3>
        """,
        unsafe_allow_html=True
    )