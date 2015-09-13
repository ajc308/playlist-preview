from celery import Celery
from flask import Flask

app = Flask(__name__)
app.config.update(
    DEBUG=True,
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)

def make_celery(app):
    c = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    c.conf.update(app.config)
    taskbase = c.Task

    class ContextTask(taskbase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return taskbase.__call__(self, *args, **kwargs)
    c.Task = ContextTask
    return c

celery = make_celery(app)