#!/bin/bash

# Create Streamlit secrets directory and write secrets from environment variable
mkdir -p /app/.streamlit
printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml

# Start FastAPI (for Safaricom webhook callbacks) on port 8000 in the background
uvicorn server:app --host 0.0.0.0 --port 8000 &

# Start Streamlit on the port required by Google Cloud Run ($PORT) in the foreground
streamlit run main.py --server.port=${PORT:-8080} --server.address=0.0.0.0