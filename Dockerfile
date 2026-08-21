FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# --- BEGIN SEO & STATIC PATCH ---
# 🚨 FIX 1: Appended [0] to extract the raw string item from the site packages array list
RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
    INDEX_HTML="$SITE_PACKAGES/streamlit/static/index.html" && \
    \
    # 1. Clean out standard default corporate comments
    sed -i '/Copyright (c) Streamlit Inc/d' "$INDEX_HTML" && \
    \
    # 2. Inject completely absolute public paths targeting actual image extensions
    # 🚨 FIX 2: Fixed the href/content URLs so they point directly to your files instead of breaking
    sed -i 's|<title>Streamlit</title>|<title>Mwalimu AI App - Smart Educational Assistant</title><meta name="description" content="Mwalimu AI App provides advanced educational assistance, lesson planning, and smart study tools for teachers and students in Kenya." /><link rel="icon" type="image/png" href="https://mwalimuaiapp.com" /><link rel="apple-touch-icon" href="https://mwalimuaiapp.com" /><meta property="og:title" content="Mwalimu AI App - Smart Educational Assistant" /><meta property="og:description" content="Mwalimu AI App provides advanced educational assistance, lesson planning, and smart study tools for teachers and students in Kenya." /><meta property="og:image" content="https://mwalimuaiapp.com" /><meta property="og:type" content="website" /><meta property="og:url" content="https://mwalimuaiapp.com" />|g' "$INDEX_HTML" && \
    \
    # 3. CRITICAL: Replaces the file directly to white-label the initial app handshake/loading tab
    cp /app/assets/favicon.png "$SITE_PACKAGES/streamlit/static/favicon.png"
# --- END SEO & STATIC PATCH ---

EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0 --server.enableStaticServing=true
