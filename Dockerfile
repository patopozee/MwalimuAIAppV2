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
    sed -i 's|<title>Streamlit</title>|<title>Mwalimu AI App - AI Tutor for Kenya CBC Curriculum</title><meta name="description" content="Mwalimu AI is an AI powered learning platform built for Kenya CBC curriculum. Get personalized AI tutoring, lessons, quizzes, flashcards, smart study plans, voice tutoring and academic progress tracking in one intelligent learning workspace." /><meta name="robots" content="index, follow" /><link rel="canonical" href="https://mwalimuaiapp.com/" /><meta property="og:title" content="Mwalimu AI App - AI Tutor for Kenya CBC Curriculum" /><meta property="og:description" content="Personalized AI tutoring, CBC aligned lessons, quizzes, flashcards, study plans, voice tutoring and progress tracking for Kenyan students." /><meta property="og:type" content="website" /><meta property="og:url" content="https://mwalimuaiapp.com/" /><meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="Mwalimu AI App - AI Tutor for Kenya CBC Curriculum" /><meta name="twitter:description" content="Your AI tutor and intelligent learning workspace for Kenya CBC curriculum." />|g' "$INDEX_HTML" &&\
    \
    # 3. CRITICAL: Replaces the file directly to white-label the initial app handshake/loading tab
    cp /app/assets/favicon.png "$SITE_PACKAGES/streamlit/static/favicon.png"
# --- END SEO & STATIC PATCH ---

EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0 --server.enableStaticServing=true
