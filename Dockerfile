FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml requirements.txt README.md ./
COPY src/ ./src/
RUN pip install . \
    && useradd --create-home --uid 10001 app
USER app

# Optional test image; tests and sample data stay out of the runtime image.
FROM base AS test
USER root
RUN pip install '.[dev]'
COPY tests/ ./tests/
COPY sql/ ./sql/
COPY data/ ./data/
COPY scripts/ ./scripts/
USER app
CMD ["python", "-m", "pytest", "-v", "-W", "error", "-p", "no:cacheprovider"]

# Default build produces only the API runtime.
FROM base AS runtime
EXPOSE 8000
CMD ["uvicorn", "clinical_data_quality.api:app", "--host", "0.0.0.0", "--port", "8000"]
