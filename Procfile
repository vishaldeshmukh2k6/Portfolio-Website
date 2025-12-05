web: gunicorn --bind 0.0.0.0:$PORT app:app
release: python -c "from app import initialize_app; initialize_app()"