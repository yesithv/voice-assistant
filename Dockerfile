FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface

RUN useradd --create-home appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn \
 && chown appuser /app

USER appuser

# Bake the Piper voice and Whisper model into the image so the container starts offline
ARG WHISPER_MODEL=small
ENV WHISPER_MODEL=${WHISPER_MODEL}
COPY --chown=appuser scripts/ scripts/
RUN python scripts/download_models.py

COPY --chown=appuser . .

EXPOSE 8000

# One worker: each worker loads its own copy of the models
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "120", "app:create_default_app()"]