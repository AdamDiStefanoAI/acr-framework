FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY examples /app/examples

RUN pip install --no-cache-dir fastapi uvicorn[standard] python-jose[cryptography]

EXPOSE 8010

CMD ["uvicorn", "examples.protected_executor.app:app", "--host", "0.0.0.0", "--port", "8010"]
