FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT env var
ENV PORT=8000
EXPOSE 8000

# 2 workers: each worker holds a full document parse + AI context in RAM,
# and 4 workers sharing the 1536M container cap OOM-kill each other on
# 50MB filings (socket hang-up mid-extraction). 2 is plenty for pilot load.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --timeout-keep-alive 300"]
