FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000 8080

RUN chmod +x run.sh

CMD [".run.sh"]