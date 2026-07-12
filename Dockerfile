FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compiling standard scientific or database extensions
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# Clean Shell Execution Evaluation String (Bypasses token interpolation limits)
CMD ["sh", "-c", "streamlit run main.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
