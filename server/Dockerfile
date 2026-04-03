FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "server.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
