#!/bin/bash
set -e

echo "Waiting for postgres to be ready..."
python << END
import socket
import time

while True:
    try:
        sock = socket.create_connection(("db", 5432), timeout=2)
        sock.close()
        break
    except (socket.error, OSError):
        print("Waiting for db:5432 ...")
        time.sleep(1)
END

echo "PostgreSQL started"

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput || true

exec "$@"
