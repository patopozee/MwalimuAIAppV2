FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    streamlit run main.py --server.port=8080 --server.address=0.0.0.0