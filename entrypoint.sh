#!/bin/bash
set -e

# Only wait for DB if running inside Docker Compose (db hostname is set)
DB_HOST="${DB_HOST:-db}"

python << END
import socket, os, time

db_host = os.getenv("DB_HOST", "db")
db_port = int(os.getenv("DB_PORT", 5432))

# Try once — if host not resolvable, skip (e.g. Render managed DB)
for i in range(10):
    try:
        sock = socket.create_connection((db_host, db_port), timeout=2)
        sock.close()
        print(f"PostgreSQL at {db_host}:{db_port} is ready!")
        break
    except (socket.error, OSError):
        if i == 0:
            print(f"Cannot reach {db_host}:{db_port}, retrying...")
        time.sleep(1)
else:
    print("DB not reachable via hostname — skipping wait (likely using DATABASE_URL on Render).")
END

python manage.py migrate --noinput || true
python manage.py collectstatic --noinput || true

exec "$@"
