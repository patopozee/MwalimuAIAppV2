import streamlit as st
from components.loaders import show_page_loader


def render(): 
    # 1. INSTANT UI FEEDBACK: Mount loader slot immediately onto screen
    loader_slot = st.empty()
    with loader_slot.container():
        show_page_loader("Loading Admin Control Center...")

    # 2. LAZY IMPORT: Load heavy admin utilities and database services
    from services.admin_page import render_admin_dashboard

    # 3. CLEAR LOADER: Remove spinner slot right before rendering dashboard UI
    loader_slot.empty()

    # 4. RENDER ADMIN DASHBOARD
    render_admin_dashboard()