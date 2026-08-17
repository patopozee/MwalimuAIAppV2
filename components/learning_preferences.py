import streamlit as st


def render():
    st.sidebar.markdown("---")

    with st.sidebar.expander(
        "⚙️ Learning Preferences",
        expanded=False,
    ):
        # 1. Learning Styles Configuration
        styles = [
            "Visual",
            "Practical",
            "Reading/Writing",
            "Interactive",
            "Story-based",
        ]
        saved_style = st.session_state.get("learning_style", styles[0])
        style_idx = styles.index(saved_style) if saved_style in styles else 0

        learning_style = st.selectbox(
            "Learning Style",
            options=styles,
            index=style_idx,
            key="learning_style_select",
        )

        # 2. Languages Configuration
        languages = ["English", "Kiswahili", "Sheng"]
        saved_lang = st.session_state.get("language", languages[0])
        lang_idx = languages.index(saved_lang) if saved_lang in languages else 0

        language = st.selectbox(
            "Preferred Language",
            options=languages,
            index=lang_idx,
            key="language_select",
        )

        # 3. Update State Directly Without Forcing st.rerun()
        st.session_state.learning_style = learning_style
        st.session_state.language = language