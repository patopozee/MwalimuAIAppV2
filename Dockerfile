FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# --- BEGIN SEO PATCH ---
# This locates index.html and injects your custom title and meta description
RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
    INDEX_HTML="$SITE_PACKAGES/streamlit/static/index.html" && \
    sed -i 's|<title>Streamlit</title>|<title>Mwalimu AI App - Smart Educational Assistant</title><meta name="description" content="Mwalimu AI App provides advanced educational assistance, lesson planning, and smart study tools for teachers and students in Kenya.">|g' "$INDEX_HTML"
# --- END SEO PATCH ---

# Replace Streamlit favicon with Mwalimu favicon
RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
cp /app/assets/favicon.png \
    "$SITE_PACKAGES/streamlit/static/favicon.png"

EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0 --server.enableStaticServing=true
