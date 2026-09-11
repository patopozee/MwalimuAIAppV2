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

        # -------------------------------------------------------------
        # 2. AUTOMATED TWO-WAY LANGUAGE SWITCHER ENGINE
        # -------------------------------------------------------------
        languages = ["English", "Kiswahili", "Sheng"]
        
        # Capture the active subject chosen from your main curriculum tree
        active_subject = str(st.session_state.get("active_subject", "General")).lower()
        
        # 🚀 THE TWO-WAY AUTOMATIC SWITCHER:
        if "kiswahili" in active_subject or "swahili" in active_subject:
            # If the subject is Kiswahili, force the dropdown to select "Kiswahili"
            lang_idx = languages.index("Kiswahili")
        else:
            # 🚀 FIX: If they switch to ANY other subject, force it to snap back to "English"
            # (Or fallback to English if no language is active in session yet)
            lang_idx = languages.index("English")

        # Use a dynamic subject-based key to force Streamlit to redraw the widget 
        # and drop its old cache the millisecond the subject changes.
        language = st.selectbox(
            "Preferred Language",
            options=languages,
            index=lang_idx,
            key=f"language_select_sync_{active_subject}",
        )

        # 3. Update State Directly Without Forcing st.rerun()
        st.session_state.learning_style = learning_style
        st.session_state.language = language
        st.session_state.preferred_language = language  # Updates both system memory variables
