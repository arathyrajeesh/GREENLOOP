FROM python:3.10-slim

# Install system utilities and GeoDjango dependencies (GDAL, PROJ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    binutils \
    libproj-dev \
    gdal-bin \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

# Copy source code and entrypoint
COPY . /app/
RUN chmod +x /app/entrypoint.sh

# Run via entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
