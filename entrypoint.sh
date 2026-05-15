#!/bin/sh
set -e

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
  echo "HOST and PORT must be set for database connection"
  exit 1
fi

echo "Waiting for database at $HOST:$PORT..."
while ! nc -z "$HOST" "$PORT"; do
  sleep 1
done

echo "Database is ready"

python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000
