import streamlit as st


def render():

    st.sidebar.markdown("---")

    with st.sidebar.expander(
        "⚙️ Learning Preferences",
        expanded=False,
    ):

        learning_style = st.selectbox(
            "Learning Style",
            [
                "Visual",
                "Practical",
                "Reading/Writing",
                "Interactive",
                "Story-based",
            ],
            key="learning_style_select",
        )

        language = st.selectbox(
            "Preferred Language",
            [
                "English",
                "Kiswahili",
                "Sheng",
            ],
            key="language_select",
        )

        if (
            learning_style
            != st.session_state.get("learning_style")
            or language
            != st.session_state.get("language")
        ):

            st.session_state.learning_style = learning_style
            st.session_state.language = language
            st.rerun()