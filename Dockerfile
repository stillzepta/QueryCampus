# QueryCampus: Production Multi-stage Dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data
COPY querycampus/ querycampus/
COPY data/ data/
COPY setup.py .
RUN pip install --no-cache-dir -e .

# Expose Streamlit port
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command
CMD ["streamlit", "run", "querycampus/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
