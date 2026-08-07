import streamlit as st

from components.subscription import render as render_subscription
from components.navigation import render as render_navigation
from components.profile import render as render_profile
from components.learning_context import render as render_learning_context
from components.learning_preferences import render as render_learning_preferences
from styles.quick_actions import render_quick_actions
from components.admin_access import render as render_admin_access
from components.test import render as render_test
from components.logout import render as render_logout
from components.metrics_dashboard import render as render_metrics_dashboard


def render():
    # ✅ FIX: Guard clause to instantly stop rendering if the user is unauthenticated
    if not st.session_state.get("user_authenticated", False):
        return

    render_navigation()
    render_profile()
    render_learning_context()
    render_learning_preferences()
    render_quick_actions()
    render_test()
    render_admin_access()
    render_subscription()
    render_logout()
    render_metrics_dashboard()
    st.sidebar.markdown("---")
