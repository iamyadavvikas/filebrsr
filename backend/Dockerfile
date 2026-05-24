FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT env var
ENV PORT=8000
EXPOSE 8000

# 4 workers for concurrent request handling (10 pilot customers)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 4 --timeout-keep-alive 300"]
