FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY ../xana_steel_core.so ../xana_audio_dsp.so ./

COPY . .

ARG XANA_GATEWAY_PORT=54446
ENV GATEWAY_PORT=${XANA_GATEWAY_PORT}
ENV PYTHONPATH=/app

EXPOSE ${XANA_GATEWAY_PORT}

CMD ["sh", "-c", "uv run uvicorn sensory.multimodal_gateway:app --host 0.0.0.0 --port ${GATEWAY_PORT}"]
