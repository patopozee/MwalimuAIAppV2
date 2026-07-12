FROM python:3.11-slim

WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

EXPOSE 8080

# Use a standard CMD; handle secrets via Cloud Run Environment Variables/Secrets
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]