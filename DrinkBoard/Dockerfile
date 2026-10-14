FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY frontend ./frontend
COPY config ./config
COPY scripts ./scripts

ENV DRINKBOARD_DB=/data/drinkboard.sqlite3 \
    DRINKBOARD_BACKUP_DIR=/data/backups \
    DRINKBOARD_DRINKS_FILE=/data/drinks.json \
    DRINKBOARD_SEED_DEMO=0 \
    DRINKBOARD_DOCS=0 \
    PYTHONDONTWRITEBYTECODE=1

VOLUME /data
EXPOSE 8773
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8773"]
