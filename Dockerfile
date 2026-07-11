FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CARDGEN_DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cardgen ./cardgen
COPY webapp ./webapp
COPY templates ./templates
COPY static ./static
COPY assets ./assets

# Non-root user; /data is the persistence volume (bind-mounted on the host).
RUN useradd -m appuser \
    && mkdir -p /data \
    && chown -R appuser /app /data
USER appuser

EXPOSE 8000
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
