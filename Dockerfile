FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY outlook/ outlook/
COPY templates/ templates/

RUN pip install --no-cache-dir -e .

# Data directory is a volume so it persists across restarts
VOLUME /app/data

CMD ["python", "-m", "outlook", "run"]
