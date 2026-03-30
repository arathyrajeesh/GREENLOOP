FROM python:3.10-slim

# Install system dependencies (GeoDjango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    binutils \
    libproj-dev \
    libgdal-dev \
    libgeos-dev \
    gdal-bin \
    netcat-openbsd \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install requirements
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

# Copy project
COPY . /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set production settings as default for Render
ENV DJANGO_SETTINGS_MODULE=greenloop.settings.production
ENV PYTHONUNBUFFERED=1

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Start server using Daphne (recommended for ASGI/Channels on Render)
CMD daphne -b 0.0.0.0 -p ${PORT:-10000} greenloop.asgi:application