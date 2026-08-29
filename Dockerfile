FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# --- BEGIN SEO & STATIC PATCH ---
# 🎯 FIX: Handled the index modification completely in Python to completely avoid shell variable and token syntax errors
RUN python -c '\
import site, os, shutil\n\
site_pkg = site.getsitepackages()[0]\n\
index_html = os.path.join(site_pkg, "streamlit", "static", "index.html")\n\
\n\
with open(index_html, "r", encoding="utf-8") as f: lines = f.readlines()\n\
lines = [l for l in lines if "Copyright (c) Streamlit Inc" not in l]\n\
content = "".join(lines)\n\
\n\
old_tag = "<title>Streamlit</title>"\n\
new_tags = """<title>Mwalimu AI App - AI Tutor for Kenya CBC/CBE & KICD Curriculum Aligned</title><meta name="description" content="Mwalimu AI App is an AI powered learning platform for Kenya CBC/CBE curriculum. Get personalized AI tutoring, CBC aligned lessons, quizzes, flashcards, smart study plans generators, voice tutoring, Learning Management System (LMS) and academic progress tracking for Kenyan students grade 1-12, you get awarded certificate by Mwalimu AI App after mastering any subject, all in one App." /><link rel="icon" type="image/png" href="https://mwalimuaiapp.com" /><link rel="apple-touch-icon" href="https://mwalimuaiapp.com" /><meta property="og:title" content="Mwalimu AI App - AI Tutor for Kenya CBC Curriculum" /><meta property="og:description" content="AI tutoring, CBC aligned lessons, quizzes, flashcards, study plans, voice tutoring and academic progress tracking for Kenyan students." /><meta property="og:image" content="https://mwalimuaiapp.com" /><meta property="og:type" content="website" /><meta property="og:url" content="https://mwalimuaiapp.com" /><meta name="robots" content="index, follow" /><link rel="canonical" href="https://mwalimuaiapp.com" /><meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="Mwalimu AI App - AI Tutor for Kenya CBC/CBE KICD Curriculum Aligned" /><meta name="twitter:description" content="Your AI tutor and intelligent learning workspace for Kenya CBC/CBE KICD curriculum Aligned." />"""\n\
\n\
content = content.replace(old_tag, new_tags)\n\
with open(index_html, "w", encoding="utf-8") as f: f.write(content)\n\
\n\
shutil.copy("/app/assets/favicon.png", os.path.join(site_pkg, "streamlit", "static", "favicon.png"))\n\
'
# --- END SEO & STATIC PATCH ---

EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0 --server.enableStaticServing=true
