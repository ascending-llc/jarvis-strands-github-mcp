FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# uv-based, lockfile-faithful install (matches uv.lock exactly)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY . /app

RUN uv sync --frozen --no-dev

# AgentCore A2A contract: stateless streamable HTTP server on port 9000 at root.
EXPOSE 9000

CMD ["uv", "run", "python", "-m", "agents.server"]
