FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY examples /app/examples

RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic-settings "PyJWT[crypto]>=2.15.1,<3.0.0"

RUN groupadd --system --gid 10001 acr \
    && useradd --system --uid 10001 --gid acr --home-dir /app --no-create-home acr

# The executor only reads application files and listens on an unprivileged port.
USER acr

EXPOSE 8010

CMD ["uvicorn", "examples.protected_executor.app:app", "--host", "0.0.0.0", "--port", "8010"]
