web: python manage.py wait_for_db --timeout=60 && python manage.py migrate && python manage.py collectstatic --noinput && python -m gunicorn moralai.wsgi --log-file -
