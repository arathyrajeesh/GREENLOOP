#!/bin/bash
set -e

# Detect environment
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "==> Starting GreenLoop Entrypoint..."

# Skip wait if on Render or using an external DATABASE_URL
SKIP_WAIT=false
if [ -n "$RENDER" ] || [ -n "$RENDER_SERVICE_ID" ]; then
    SKIP_WAIT=true
    echo "==> Render environment detected."
elif [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" != *"@db"* ]] && [[ "$DATABASE_URL" != *"@localhost"* ]]; then
    SKIP_WAIT=true
    echo "==> External database detected."
fi

if [ "$SKIP_WAIT" = "true" ]; then
    echo "==> Skipping database reachability check."
else
    echo "==> Waiting for PostgreSQL at $DB_HOST:$DB_PORT ..."
    python << END
import socket, os, time
db_host = "$DB_HOST"
db_port = int("$DB_PORT")

for i in range(15):
    try:
        sock = socket.create_connection((db_host, db_port), timeout=2)
        sock.close()
        print(f"PostgreSQL at {db_host}:{db_port} is ready!")
        exit(0)
    except (socket.error, OSError):
        time.sleep(1)
print(f"PostgreSQL at {db_host}:{db_port} not reachable, proceeding anyway...")
END
fi

# Run migrations and collectstatic
echo "==> Running migrations..."
python manage.py migrate --noinput || echo "==> Migration failed, but proceeding..."

echo "==> Collecting static files..."
python manage.py collectstatic --noinput || echo "==> Collectstatic failed, but proceeding..."

echo "==> Environment Check:"
echo "    PORT: $PORT"
echo "    DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

echo "==> Executing start command: $@"
exec "$@"
