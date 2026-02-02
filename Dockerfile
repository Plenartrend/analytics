# syntax=docker/dockerfile:1.20

FROM astral/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy


COPY pyproject.toml uv.lock ./

COPY --parents packages/*/src/*/__init__.py .
COPY --parents packages/*/pyproject.toml .
COPY --parents packages/*/README.md .

RUN uv sync --frozen --no-dev --no-cache

# spaCy-Modell in der Builder-Stage herunterladen (als root, mit Netzwerkzugang)
RUN ./.venv/bin/python -m spacy download de_core_news_sm

RUN \
  rm -rf \
    /root/.cache \
    /tmp/* \
    /app/.venv/share \
    /app/.venv/lib/python*/site-packages/**/tests \
    /app/.venv/lib/python*/site-packages/**/__pycache__

FROM python:3.13-slim AS runner

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
