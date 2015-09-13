web: gunicorn tasks:app --log-file=- --loglevel=DEBUG
worker: celery -A tasks.celery worker --loglevel=DEBUG
