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

# Ensure assets (fonts, placeholder image) are world-readable so the app can
# open them when the container runs as an arbitrary non-root user.
RUN chmod -R a+rX /app/assets /app/static /app/templates

# The app writes cards to CARDGEN_DATA_DIR (default /data). Mount a directory
# there at run time and run as a user that owns it (docker run --user / compose
# `user:`). The image intentionally does not create /data, declare a VOLUME, or
# fix a user — the mount supplies the path, ownership, and permissions.

EXPOSE 8000
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
