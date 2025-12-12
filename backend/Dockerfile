FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for lockfile-aware installs
RUN pip install --no-cache-dir uv

# Copy dependency definitions and install dependencies via uv (uses pyproject.toml + uv.lock)
COPY ./pyproject.toml ./uv.lock ./
RUN uv pip install --system --no-cache .

# Copy application code
COPY ./ ./
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "heatpump_stats.entrypoints.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
