FROM python:3.10-slim

# Install system dependencies (GeoDjango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    binutils \
    libproj-dev \
    gdal-bin \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install requirements
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

# Copy project
COPY . /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# 🔥 START SERVER (IMPORTANT)
CMD ["sh", "-c", "gunicorn greenloop.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT"]