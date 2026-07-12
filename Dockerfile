FROM python:3.11-slim

WORKDIR /app

# 1. Install dependencies first (for faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the entire project, including the .streamlit folder
COPY . .

# 3. No need to echo secrets anymore. Just run the app.
# Streamlit will automatically look for .streamlit/secrets.toml inside /app
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]