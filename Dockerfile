# syntax=docker/dockerfile:1.20

# Da github action schelcht ist, darf ich jetzt uv manuel installieren
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy


COPY pyproject.toml uv.lock ./

COPY --parents packages/*/src/*/__init__.py .
COPY --parents packages/*/pyproject.toml .
COPY --parents packages/*/README.md .

RUN uv sync --frozen --no-dev --no-cache

RUN \
  rm -rf \
    /root/.cache \
    /tmp/* \
    /app/.venv/share \
    /app/.venv/lib/python*/site-packages/**/tests \
    /app/.venv/lib/python*/site-packages/**/__pycache__

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

CMD ["sh", "-c", "python -m spacy download de_core_news_sm && alembic upgrade head && python -m src.app"]
