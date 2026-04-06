# ──────────────────────────────────────────────────────────────────────────────
# Dockerfile
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Run with Gunicorn (production WSGI server — handles concurrent requests)
CMD ["gunicorn", "brewmate.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "60", \
     "--access-logfile", "-"]


# ──────────────────────────────────────────────────────────────────────────────
# docker-compose.yml — Local development setup
# ──────────────────────────────────────────────────────────────────────────────
# version: "3.9"
#
# services:
#
#   api:
#     build: .
#     ports:
#       - "8000:8000"
#     environment:
#       - SECRET_KEY=local-dev-secret-key-change-in-prod
#       - DEBUG=True
#       - DB_NAME=brewmate_db
#       - DB_USER=brewmate_user
#       - DB_PASSWORD=brewmate_pass
#       - DB_HOST=db
#       - REDIS_URL=redis://redis:6379/1
#     depends_on:
#       - db
#       - redis
#     volumes:
#       - .:/app
#     command: python manage.py runserver 0.0.0.0:8000
#
#   db:
#     image: postgres:15-alpine
#     environment:
#       POSTGRES_DB: brewmate_db
#       POSTGRES_USER: brewmate_user
#       POSTGRES_PASSWORD: brewmate_pass
#     volumes:
#       - postgres_data:/var/lib/postgresql/data
#     ports:
#       - "5432:5432"
#
#   redis:
#     image: redis:7-alpine
#     ports:
#       - "6379:6379"
#
#   nginx:
#     image: nginx:alpine
#     ports:
#       - "80:80"
#     volumes:
#       - ./nginx.conf:/etc/nginx/nginx.conf
#     depends_on:
#       - api
#
# volumes:
#   postgres_data:
