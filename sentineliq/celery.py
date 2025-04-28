import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentineliq.settings")

# Create a Celery instance and configure it using the settings from Django
app = Celery("sentineliq")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Task to verify that Celery is working."""
    print(f"Request: {self.request!r}")
    return "Celery is working!"
