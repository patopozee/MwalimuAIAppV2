FROM python:3.11-slim

WORKDIR /app

# Only install standard extensions. We dropped software-properties-common to fix the crash
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["sh", "-c", "streamlit run main.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
