#!bin/sh
set -e

chown -R nobody:nogroup /app_data

celery -A geoprocessor.tasks.celery_app \
    worker --loglevel=info --concurrency=1 --uid=nobody --gid=nogroup