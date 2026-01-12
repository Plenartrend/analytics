# Builder stage
FROM ghcr.io/astral-sh/uv:python3.14-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Build sub-dependencies
COPY packages/ packages/
RUN cd packages/podi && uv build --package podi
RUN cd packages/pipeline && uv build --package pipeline
RUN cd packages/pipeline && uv build --package hashrr

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

RUN uv pip install /app/packages/podi/dist/podi-*.whl
RUN uv pip install /app/packages/pipeline/dist/pipeline-*.whl
RUN uv pip install /app/packages/hashrr/dist/hashrr-*.whl

# Runner stage
FROM python:3.14-slim AS runner

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY src/ src/

ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "src/app/main.py"]
