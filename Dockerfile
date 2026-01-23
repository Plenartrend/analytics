# syntax=docker/dockerfile:1.4
FROM astral/uv:python3.14-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

COPY --parents packages/*/src/*/__init__.py .
COPY --parents packages/*/pyproject.toml .
COPY --parents packages/*/README.md .

RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runner

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

RUN mkdir logs
RUN chown -R nonroot:nonroot logs

COPY --from=builder --chown=nonroot:nonroot  /app/.venv .venv
COPY --chown=nonroot:nonroot packages/ packages/
COPY --chown=nonroot:nonroot src/ src/

COPY --chown=nonroot:nonroot alembic.ini .
COPY --chown=nonroot:nonroot alembic/ alembic/

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "alembic upgrade head && python -m src.app"]
