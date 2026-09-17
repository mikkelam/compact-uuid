# compact_uuid benchmark results

Generated: `2026-09-17T13:36:31Z`

## Configuration

- Rows: 500,000
- Paired repetitions: 7
- Duration per variant: 5 seconds
- pgbench clients/workers: 8/4
- Host: `macOS-15.7.3-arm64-64bit-Mach-O` (`arm64`)
- Container CPUs: 6
- Container memory limit: `max`
- PostgreSQL: `PostgreSQL 18.6 (Debian 18.6-1.pgdg12+2) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit`

## Paired workload results

| Workload | Native latency | Compact latency | Absolute delta | Latency delta (95% CI) | Throughput delta (95% CI) |
| --- | ---: | ---: | ---: | ---: | ---: |
| lookup | 0.0323 ms | 0.0366 ms | +4.30 µs | +13.31% (-0.93%–+31.85%) | -11.84% (-24.44%–+0.82%) |
| interop | 0.0317 ms | 0.0464 ms | +14.70 µs | +46.45% (+22.65%–+75.21%) | -31.94% (-42.96%–-18.18%) |
| input | 0.0320 ms | 0.0397 ms | +7.66 µs | +23.94% (+4.91%–+49.51%) | -19.75% (-33.32%–-4.68%) |
| output | 0.0552 ms | 0.0606 ms | +5.44 µs | +9.86% (-3.96%–+21.74%) | -9.18% (-17.78%–+3.88%) |
| range | 0.0335 ms | 0.0390 ms | +5.55 µs | +16.57% (+9.27%–+23.95%) | -14.70% (-19.80%–-9.11%) |
| insert | 1.6017 ms | 1.6877 ms | +86.05 µs | +5.37% (-1.57%–+10.89%) | -5.08% (-9.76%–+1.59%) |

## Static measurements

| Measurement | Native UUID | compact_uuid |
| --- | ---: | ---: |
| Datum size | 16 B | 16 B |
| Text length | 36 chars | 22 chars |
| Heap size | 63,021,056 B | 63,021,056 B |
| Primary index size | 19,734,528 B | 19,734,528 B |
| Total relation size | 94,060,544 B | 94,060,544 B |

Ratios are paired compact/native geometric means. Lower latency and higher throughput are better.
