FROM node:24.13.1-bookworm-slim AS node
FROM rust:1.90-slim-bookworm AS host
WORKDIR /src
COPY host/ ./
RUN cargo test --locked && cargo build --release --locked

FROM python:3.12-slim-bookworm AS tests
RUN apt-get update && apt-get install -y --no-install-recommends libegl1 libopengl0 libglib2.0-0 libportaudio2 libdbus-1-3 libfontconfig1 libxkbcommon0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY pyproject.toml ./
COPY arise_app/ arise_app/
COPY assets/ assets/
RUN pip install --no-cache-dir .
COPY vendor/package*.json vendor/
RUN npm ci --prefix vendor --ignore-scripts --no-audit --no-fund
COPY web/ web/
COPY tests/ tests/
COPY scripts/test.py scripts/test.py
COPY --from=host /src/target/release/arise-host /app/ARISE-host
ENV QT_QPA_PLATFORM=offscreen PI_OFFLINE=1 PI_TELEMETRY=0 ARISE_TEST_REPORT=/results/test-results.json
CMD ["python", "scripts/test.py"]
