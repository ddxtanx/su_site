web: gunicorn --timeout 90 --worker-class eventlet -w 1 main:app
worker: celery -A server.tasks worker --loglevel warning --concurrency 5 -E -Ofair
