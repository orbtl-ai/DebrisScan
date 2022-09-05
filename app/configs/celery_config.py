from os import getenv

print('=== CELERY_CONFIG.PY ===')
print(f"CELERY_BROKER_URL: {getenv('CELERY_BROKER_URL')}")
print(f"CELERY_RESULT_BACKEND: {getenv('CELERY_RESULT_BACKEND')}")
print(f"TASK_TRACK_STARTED: {getenv('TASK_TRACK_STARTED')}")

celery_app_name: str = getenv('CELERY_APP_NAME', 'dart-api')
broker_url: str = getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend: str = getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
