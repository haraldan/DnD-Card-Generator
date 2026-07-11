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

# Default data location. Mount your own directory here and choose the runtime
# user (docker run --user / compose `user:`) so the app can write to it. The
# image does not declare a VOLUME (that would spawn anonymous volumes on runs
# that forget the mount) and does not fix a user itself. /data is made
# world-writable so the default path works for any runtime user when no volume
# is mounted; once you mount your own directory here, that mount's ownership and
# permissions take over and this chmod is irrelevant.
RUN mkdir -p /data && chmod 0777 /data

EXPOSE 8000
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
