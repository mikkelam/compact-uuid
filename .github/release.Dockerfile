ARG PG_VERSION=18.6

FROM postgres:${PG_VERSION}-bookworm

COPY . /
