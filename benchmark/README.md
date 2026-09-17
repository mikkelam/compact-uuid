# Benchmarks

The benchmark suite compares `compact_uuid` with PostgreSQL's native `uuid`
inside the same PostgreSQL 18 container. `pgbench` runs over the container's
Unix socket, avoiding host networking and client-driver overhead.

```fish
mise run benchmark
```

Defaults use 500,000 source rows, seven paired repetitions, eight clients, four
workers, and ten seconds per variant. A full run takes roughly 12 minutes after
the Docker image is cached. For a quick infrastructure check:

```fish
mise run benchmark -- --rows 10000 --repetitions 2 --duration 1
```

Each repetition runs the native and compact variants in randomized order. The
report shows the geometric mean compact/native ratio and a paired 95% bootstrap
confidence interval. Values below 1.0 mean lower compact latency; values above
1.0 mean higher compact throughput.

The workloads cover same-type indexed lookup, lookup through a native UUID value,
text input, 100-row text output, ordered index scans, and inserts. Keeping the two
lookup paths separate distinguishes the core type cost from interoperability
operator cost. Static measurements cover heap/index size, in-memory datum size,
and output length. Results are written to `benchmark/results/latest.json` and
`benchmark/results/latest.md`.

Before timing, the runner verifies that each native/compact workload pair has
the same execution-plan node shape. Full plans are retained in the raw JSON.

This is a microbenchmark. Run it on an otherwise idle machine, keep Docker's CPU
and memory allocation fixed, and publish the raw JSON with any claimed result.
Do not compare results produced with different PostgreSQL, pgrx, hardware, or
container-resource settings.
