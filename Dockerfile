FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# --- BEGIN SEO & STATIC PATCH ---
# Locates Streamlit's static directory and patches index.html + favicon
RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
    INDEX_HTML="$SITE_PACKAGES/streamlit/static/index.html" && \
    \
    # 1. Remove the Streamlit/Snowflake copyright comment header
    sed -i '/Copyright (c) Streamlit Inc/d' "$INDEX_HTML" && \
    \
    # 2. Inject custom Title and Meta Description
    sed -i 's|<title>Streamlit</title>|<title>Mwalimu AI App - Smart Educational Assistant</title><meta name="description" content="Mwalimu AI App provides advanced educational assistance, lesson planning, and smart study tools for teachers and students in Kenya." />|g' "$INDEX_HTML" && \
    \
    # 3. Replace default favicon with Mwalimu AI logo
    cp /app/assets/favicon.png "$SITE_PACKAGES/streamlit/static/favicon.png"
# --- END SEO & STATIC PATCH ---

ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_SERVER_ADDRESS="app.mwalimuaiapp.com"
ENV STREAMLIT_BROWSER_SERVER_PORT=443

EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0 --server.enableStaticServing=true