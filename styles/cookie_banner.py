#styles/cookie_banner.py
import streamlit as st

def load():
    # 1. Inject the pure CSS layout configuration rules
    st.markdown(
        """
        <style>
        /* Floating Fixed Cookie Box Shell */
        .mw-cookie-popup {
            position: fixed !important;
            bottom: 0px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(900px, calc(100vw - 40px)) !important;
            background-color: #101726 !important; /* Premium unified dark navy container */
            border: 1px solid rgba(36, 115, 242, 0.25) !important;
            border-radius: 14px !important;
            box-shadow: 0 -10px 35px rgba(0, 0, 0, 0.6) !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 16px 24px !important;
            z-index: 999999 !important;
            box-sizing: border-box !important;
            gap: 20px !important;
        }

        /* Banner Paragraph Content styling rules */
        .mw-cookie-text {
            margin: 0 !important;
            padding: 0 !important;
            font-size: 0.9rem !important;
            color: #94A3B8 !important;
            line-height: 1.5 !important;
            font-family: sans-serif !important;
        }

        .mw-cookie-link {
            color: #2473F2 !important;
            text-decoration: none !important;
            font-weight: 600 !important;
        }
        
        .mw-cookie-link:hover {
            text-decoration: underline !important;
        }

        /* Pure HTML native button element layouts */
        .mw-cookie-btn-group {
            display: flex !important;
            gap: 10px !important;
            flex-shrink: 0 !important;
        }

        .mw-cookie-btn {
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            padding: 10px 20px !important;
            cursor: pointer !important;
            border: 1px solid #2E394D !important;
            transition: all 0.2s ease-in-out !important;
        }

        .mw-cookie-btn.reject {
            background-color: #1F2937 !important;
            color: #E5E7EB !important;
        }

        .mw-cookie-btn.reject:hover {
            background-color: #2E394D !important;
        }

        .mw-cookie-btn.accept {
            background-color: #2473F2 !important;
            color: white !important;
            border: none !important;
        }

        .mw-cookie-btn.accept:hover {
            background-color: #1D4ED8 !important;
            box-shadow: 0 4px 14px rgba(36, 115, 242, 0.4) !important;
        }

        /* Mobile Adjustments (Stacks elements cleanly on phones) */
        @media (max-width: 768px) {
            .mw-cookie-popup {
                flex-direction: column !important;
                align-items: stretch !important;
                padding: 16px !important;
                bottom: 10px !important;
                gap: 14px !important;
            }
            .mw-cookie-btn-group {
                width: 100% !important;
            }
            .mw-cookie-btn {
                flex: 1 !important;
                text-align: center !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )
