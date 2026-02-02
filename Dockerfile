# syntax=docker/dockerfile:1.20

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

RUN ./.venv/bin/python -m spacy download de_core_news_sm

RUN \
  rm -rf \
    /root/.cache \
    /tmp/* \
    /app/.venv/share \
    /app/.venv/lib/python*/site-packages/**/tests \
    /app/.venv/lib/python*/site-packages/**/__pycache__

RUN chmod -R a+rX /app/.venv && chmod -R a+x /app/.venv/bin/*

FROM python:3.13-slim AS runner

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

RUN mkdir logs && chown -R nonroot:nonroot logs

COPY --from=builder /app/.venv .venv
COPY --chown=nonroot:nonroot packages/ packages/
COPY --chown=nonroot:nonroot src/ src/

COPY --chown=nonroot:nonroot alembic.ini .
COPY --chown=nonroot:nonroot alembic/ alembic/

RUN rm -f .venv/bin/python .venv/bin/python3 .venv/bin/python3.13 && \
    ln -s /usr/local/bin/python .venv/bin/python && \
    ln -s /usr/local/bin/python .venv/bin/python3 && \
    ln -s /usr/local/bin/python .venv/bin/python3.13 && \
    chmod -R a+rX .venv && \
    chmod a+x .venv/bin/* && \
    chown -R nonroot:nonroot .venv

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

CMD ["sh", "-c", "alembic upgrade head && python -m src.app"]
