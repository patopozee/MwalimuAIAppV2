# components/loaders.py
import streamlit as st

def show_page_loader(message="Loading view..."):
    st.markdown(
        f"""
        <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .page-loader-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 60px 20px;
            margin: 40px auto;
            max-width: 400px;
            background-color: #101726;
            border: 1px solid rgba(36, 115, 242, 0.2);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            text-align: center;
        }}
        .loader-spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255, 75, 75, 0.15);
            border-top: 4px solid #FF4B4B;
            border-radius: 50%;
            animation: spin 0.9s linear infinite;
            margin-bottom: 16px;
        }}
        .loader-text {{
            color: #E2E8F0;
            font-size: 15px;
            font-weight: 500;
            font-family: sans-serif;
        }}
        </style>
        <div class="page-loader-wrapper">
            <div class="loader-spinner"></div>
            <div class="loader-text">{message}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_with_loader(view_func, title="Loading View"):
    """Mounts loader instantly before heavy view logic runs."""
    loader_slot = st.empty()
    
    # 1. Instantly render loader
    with loader_slot.container():
        show_page_loader(f"Loading {title}...")
    
    # 2. Run the view logic
    view_func()
    
    # 3. Clear loader container once view has loaded
    loader_slot.empty()