ARG PG_VERSION=18.6

FROM postgres:${PG_VERSION}-bookworm AS builder

ARG PGRX_VERSION=0.19.2
ARG NEXTEST_VERSION=0.9.143
ARG RUST_VERSION=1.97.1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        build-essential \
        ca-certificates \
        clang \
        curl \
        libclang-dev \
        libpq-dev \
        pkg-config \
        postgresql-server-dev-${PG_MAJOR} \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/root/.cargo/bin:$PATH

RUN curl --proto '=https' --tlsv1.2 --silent --show-error --fail https://sh.rustup.rs \
        | sh -s -- -y --profile minimal --default-toolchain ${RUST_VERSION} \
    && cargo install cargo-pgrx --version ${PGRX_VERSION} --locked \
    && cargo install cargo-nextest --version ${NEXTEST_VERSION} --locked \
    && cargo pgrx init --pg${PG_MAJOR} "$(command -v pg_config)"

WORKDIR /workspace
COPY Cargo.toml Cargo.lock compact_uuid.control ./
COPY src ./src
COPY sql ./sql

RUN cargo nextest run --locked \
    && cargo pgrx package --pg-config "$(command -v pg_config)" --out-dir /package

FROM postgres:${PG_VERSION}-bookworm

COPY --from=builder /package/ /
COPY benchmark/sql /benchmark/sql
