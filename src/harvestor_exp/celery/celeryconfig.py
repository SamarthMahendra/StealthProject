# celeryconfig.py

broker_url = "redis://localhost:6379/0"  # For the task queue
result_backend = "redis://localhost:6379/1"  # For storing task results

# Optional: other Celery settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
