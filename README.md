# compact_uuid

**Short UUIDs for PostgreSQL: 22 characters instead of 36, with the same
16-byte storage.**

<p align="center">
  <img src="compact-uuid.png" alt="A standard UUID URL compared with a compact UUID URL" width="65%">
</p>

`compact_uuid` renders UUIDs as canonical, unpadded Base64url. Use clean IDs in
URLs and APIs without storing strings or scattering encoding helpers across
every client.

Indexed lookups measured ~4 µs slower than native UUID.

```sql
CREATE EXTENSION compact_uuid;

SELECT '550e8400-e29b-41d4-a716-446655440000'::compact_uuid;
-- VQ6EAOKbQdSnFkRmVUQAAA

SELECT 'VQ6EAOKbQdSnFkRmVUQAAA'::compact_uuid::uuid;
-- 550e8400-e29b-41d4-a716-446655440000
```

## Features

- Canonical 22-character Base64url output; accepts compact and standard UUID
  input.
- Native-sized 16-byte storage.
- B-tree and hash indexes, primary keys, foreign keys, arrays, and binary COPY.
- Lossless casts and indexed comparisons with native `uuid` values.

## Why not translate in the client?

Client-side encoding is simple until every language, service, migration, script,
and database tool needs its own implementation. A PostgreSQL type provides one
canonical representation and validation boundary while retaining UUID storage,
ordering, casts, and indexes. Text-protocol clients receive compact IDs without
application helpers; clients using binary codecs can continue handling the same
16 UUID bytes.

## UUID compatibility

Mixed `compact_uuid`/`uuid` comparisons participate in PostgreSQL's UUID
operator families, so UUID-typed parameters can use indexes without explicit
casts. Mixed-type joins should use `ON compact_id = uuid_id`; `JOIN ... USING`
would require bidirectional implicit casts, which can make unrelated SQL
function and operator resolution ambiguous.

## Installation

The extension currently supports PostgreSQL 18. Install the matching pgrx CLI,
register your PostgreSQL installation, then build and install from source:

```fish
cargo install cargo-pgrx --version 0.19.2 --locked
cargo pgrx init --pg18 (command -s pg_config)
cargo pgrx install --release --pg-config (command -s pg_config)
```

Enable it in each database where the type should be available:

```fish
psql --dbname your_database --command 'CREATE EXTENSION compact_uuid;'
```

Installing and enabling the extension requires PostgreSQL server development
headers and sufficient permission to install extension files and create a
superuser-only extension.

## Development

Docker builds and packages the extension against PostgreSQL 18. Testcontainers
starts a PostgreSQL instance from that image and removes it after the suite.
The host needs Docker, mise, and uv; it does not need PostgreSQL, Rust, pgrx, or
compiler headers.

```fish
mise run test
```

The image build runs the Rust tests with nextest. The Python integration suite
then verifies installation, text and binary protocols, storage size, casts,
ordering, B-tree and hash indexes, mixed-type queries and joins, foreign keys,
arrays, column migrations, binary COPY, dump/restore, schema relocation, and
extension removal/reinstallation with psycopg and asyncpg.

Build the development database image without running the integration suite:

```fish
mise run image
```

The extension currently targets PostgreSQL 18 and pgrx 0.19.2.

## Benchmarks

Compared with native `uuid` over 500,000 rows using seven paired pgbench runs:

| Workload | Native | `compact_uuid` | Observed cost |
| --- | ---: | ---: | ---: |
| Same-type indexed lookup | 32.3 µs | 36.6 µs | +4.3 µs |
| Lookup using a native UUID | 31.7 µs | 46.4 µs | +14.7 µs |
| Text input | 32.0 µs | 39.7 µs | +7.7 µs |
| 100-row text output | 55.2 µs | 60.6 µs | +5.4 µs |
| Ordered index scan | 33.5 µs | 39.0 µs | +5.6 µs |
| Insert | 1.602 ms | 1.688 ms | +0.086 ms |
| Stored datum | 16 bytes | 16 bytes | 0 bytes |
| Text representation | 36 chars | 22 chars | −14 chars |

See the [full report](benchmark/results/latest.md) for configuration, confidence
intervals, throughput, raw measurements, and the reproducible benchmark command.
