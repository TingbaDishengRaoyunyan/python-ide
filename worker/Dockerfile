FROM python:3.11-slim
RUN useradd -m -u 10001 worker
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
USER worker
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","9000"]
