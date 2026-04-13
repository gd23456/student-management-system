FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ templates/

# Create data directory for SQLite
RUN mkdir -p /data

# Environment
ENV DB_PATH=/data/students.db
ENV SECRET_KEY=change-me-in-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Init DB and start server
CMD ["python", "-c", "import app; app.init_db(); app.app.run(host='0.0.0.0', port=5000)"]
