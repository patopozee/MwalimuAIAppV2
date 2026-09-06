FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# --- BEGIN SEO & STATIC PATCH ---
# 🚨 FIX 1: Appended [0] to extract the raw string item from the site packages array list
# --- START SEO & STATIC PATCH ---
RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
    INDEX_HTML="$SITE_PACKAGES/streamlit/static/index.html" && \
    \
    # 1. Clean out standard default corporate comments
    sed -i '/Copyright (c) Streamlit Inc/d' "$INDEX_HTML" && \
    \
    # 2. Inject Meta Tags, Descriptions, and Title elements into the Head section
    sed -i 's|<title>Streamlit</title>|<title>Mwalimu AI App - AI Tutor for Kenya CBC, CBE \& KICD Curriculum Aligned</title><meta name="description" content="Mwalimu AI App is an AI powered learning platform for Kenya CBC/CBE curriculum. Get personalized AI tutoring, CBC aligned lessons, quizzes, flashcards, smart study plans generators, voice tutoring, Learning Management System (LMS) and academic progress tracking for Kenyan students grade 1-12, you get awarded certificate by Mwalimu AI App after mastering any subject, all in one App." /><link rel="icon" type="image/png" href="https://mwalimuaiapp.com" /><link rel="apple-touch-icon" href="https://mwalimuaiapp.com" /><meta property="og:title" content="Mwalimu AI App - AI Tutor for Kenya CBC Curriculum" /><meta property="og:description" content="AI tutoring, CBC aligned lessons, quizzes, flashcards, study plans, voice tutoring Kenyan Accent and academic progress tracking for Kenyan students." /><meta property="og:image" content="https://mwalimuaiapp.com" /><meta property="og:type" content="website" /><meta property="og:url" content="https://mwalimuaiapp.com" /><meta name="robots" content="index, follow" /><link rel="canonical" href="https://mwalimuaiapp.com" /><meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="Mwalimu AI App - AI Tutor for Kenya CBC/CBE KICD Curriculum Aligned" /><meta name="twitter:description" content="Your AI tutor and intelligent learning workspace for Kenya CBC/CBE KICD curriculum Aligned." />|g' "$INDEX_HTML" && \
    \
    # 3. NEW FEATURE: Inject Schema.org JSON-LD Structured Data to rank for QA questions
    sed -i 's|<head>|<head><script type="application/ld+json">{"@context":"https://schema.org","@type":"WebApplication","name":"Mwalimu AI App","url":"https://mwalimuaiapp.com","description":"Adaptive AI tutoring platform for Kenya CBC curriculum grade 1-12. Contains automated quiz creators and flashcard makers.","applicationCategory":"EducationalApplication","operatingSystem":"All"}</script>|g' "$INDEX_HTML" && \
    \
    # 4. NEW FEATURE: Inject extensive static keyword text right into the Noscript payload container
    sed -i 's|<div id="root"></div>|<div id="root"></div><noscript><div style="padding:20px; font-family:sans-serif; max-width:800px; margin:0 auto;"><header><h1>Mwalimu AI App – The Intelligent Study Companion</h1><p>Mwalimu AI is an adaptive digital learning partner engineered specifically for the Kenyan Competency-Based Curriculum (CBC), CBE, and KICD frameworks. Our artificial intelligence system helps primary and secondary school learners excel in their studies through tailored resource generation.</p></header><hr><section><h2>Comprehensive CBC Revision \& Test Preparation Features</h2><ul><li><strong>Automated Quiz Generator:</strong> Instantly create custom assessment tests, multiple-choice tracking questionnaires, and topical review exams to measure mastery indicators.</li><li><strong>Active Recall Flashcard Maker:</strong> Generate printable or digital study cards to boost long-term memory knowledge, ideal for vocabulary drills and lesson summaries.</li><li><strong>AI Voice Tutor Workspaces:</strong> Engage in real-time guided interactive learning paths to master complex assignments and curriculum tracking modules.</li></ul></section><hr><section><h2>Tailored National Curriculum Subject Coverage</h2><p>Our adaptive study generators cover major primary and secondary school subjects including Mathematics, Science and Technology, English, Kiswahili (Swahili), Social Studies, and Agriculture. Students can select their grade, choose a target topic module, and initialize dynamic tracking metrics.</p></section><hr><section><h2>Frequently Asked Questions (FAQ) Hub</h2><h3>How do I generate a personalized CBC study plan?</h3><p>Sign up or access your active student dashboard workspace to filter content by level and launch automated lesson plans targeted to your weak topics.</p><h3>Can teachers use Mwalimu AI App to create worksheets?</h3><p>Yes, educators can utilize our AI generators to output custom curriculum homework matrices, quiz sheets, and lesson planning templates safely.</p></section><footer><p>Access your student profile dashboard to view live learning statistics, track performance trends, and check national leaderboard score matrices.</p></footer></div></noscript>|g' "$INDEX_HTML" && \
    \
    # 5. Replaces the favicon asset directly to complete white-label configuration execution
    cp /app/assets/favicon.png "$SITE_PACKAGES/streamlit/static/favicon.png"
# --- END SEO & STATIC PATCH ---


EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0 --server.enableStaticServing=true --client.showErrorDetails=false
