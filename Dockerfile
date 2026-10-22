# Research console image (Streamlit) -- preserved as-is per
# docs/production/ARCHITECTURE_DECISIONS.md #4. See Dockerfile.api for the
# production backend service.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m -u 1000 quimrag && chown -R quimrag:quimrag /app
USER quimrag
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')" || exit 1
CMD ["streamlit","run","app.py","--server.port=8501","--server.address=0.0.0.0"]
