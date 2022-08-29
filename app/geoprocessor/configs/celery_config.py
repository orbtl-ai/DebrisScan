import os

print('=== CELERY_CONFIG.PY ===')
print(f"CELERY_BROKER_URL: {os.getenv('CELERY_BROKER_URL')}")
print(f"CELERY_RESULT_BACKEND: {os.getenv('CELERY_RESULT_BACKEND')}")
print(f"TASK_TRACK_STARTED: {os.getenv('TASK_TRACK_STARTED')}")

celery_app_name: str = os.getenv('CELERY_APP_NAME', 'dart-api')
broker_url: str = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend: str = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
