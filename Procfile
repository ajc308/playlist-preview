web: gunicorn tasks:app --log-file=-
worker: celery -A tasks.celery worker --loglevel=DEBUG
