"""Run paired pgbench workloads against native and compact UUIDs."""

import argparse
from contextlib import nullcontext
import json
import math
from pathlib import Path
import platform
import random
import re
import statistics
import time

import psycopg
from testcontainers.core.image import DockerImage
from testcontainers.community.postgres import PostgresContainer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = "compact-uuid:benchmark"
WORKLOADS = ("lookup", "interop", "input", "output", "range", "insert")


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=500_000)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260917)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    if args.rows < 100:
        parser.error("--rows must be at least 100")
    if min(args.repetitions, args.duration, args.clients, args.jobs) < 1:
        parser.error("repetitions, duration, clients, and jobs must be positive")
    return args


def setup_database(connection, rows):
    with psycopg.connect(**connection, autocommit=True) as db:
        db.execute("CREATE EXTENSION compact_uuid")
        db.execute(
            """
            CREATE TABLE benchmark_ids (
                n bigint PRIMARY KEY,
                id uuid NOT NULL UNIQUE,
                compact_id compact_uuid NOT NULL UNIQUE
            );
            """
        )
        db.execute(
            """
            INSERT INTO benchmark_ids
            SELECT n, id, id
            FROM (
                SELECT n, gen_random_uuid() AS id
                FROM generate_series(1, %s) AS n
            ) AS generated
            """,
            (rows,),
        )
        db.execute(
            """
            CREATE TABLE native_ids (
                id uuid PRIMARY KEY,
                n bigint NOT NULL UNIQUE,
                payload text NOT NULL
            );
            CREATE TABLE compact_ids (
                id compact_uuid PRIMARY KEY,
                n bigint NOT NULL UNIQUE,
                payload text NOT NULL
            );
            INSERT INTO native_ids
            SELECT id, n, repeat('x', 64) FROM benchmark_ids;
            INSERT INTO compact_ids
            SELECT id, n, repeat('x', 64) FROM benchmark_ids;

            CREATE TABLE benchmark_inputs AS
            SELECT n, id::text AS native_text, id::compact_uuid::text AS compact_text
            FROM benchmark_ids;
            CREATE UNIQUE INDEX benchmark_inputs_n_idx ON benchmark_inputs(n);

            CREATE TABLE native_writes (
                id uuid PRIMARY KEY,
                payload text NOT NULL
            );
            CREATE TABLE compact_writes (
                id compact_uuid PRIMARY KEY,
                payload text NOT NULL
            );
            """
        )
        db.execute("VACUUM ANALYZE benchmark_ids")
        db.execute("VACUUM ANALYZE native_ids")
        db.execute("VACUUM ANALYZE compact_ids")
        db.execute("VACUUM ANALYZE benchmark_inputs")


def static_measurements(connection):
    with psycopg.connect(**connection) as db:
        row = db.execute(
            """
            SELECT
                version(),
                pg_relation_size('native_ids'),
                pg_relation_size('compact_ids'),
                pg_relation_size('native_ids_pkey'),
                pg_relation_size('compact_ids_pkey'),
                pg_total_relation_size('native_ids'),
                pg_total_relation_size('compact_ids'),
                (SELECT avg(pg_column_size(id))::float8 FROM native_ids),
                (SELECT avg(pg_column_size(id))::float8 FROM compact_ids),
                (SELECT avg(length(id::text))::float8 FROM native_ids),
                (SELECT avg(length(id::text))::float8 FROM compact_ids)
            """
        ).fetchone()
    keys = (
        "postgres_version",
        "native_heap_bytes",
        "compact_heap_bytes",
        "native_primary_index_bytes",
        "compact_primary_index_bytes",
        "native_total_bytes",
        "compact_total_bytes",
        "native_datum_bytes",
        "compact_datum_bytes",
        "native_text_chars",
        "compact_text_chars",
    )
    return dict(zip(keys, row))


def query_plans(connection):
    queries = {
        "lookup_native": """
            SELECT i.payload FROM native_ids i
            JOIN benchmark_ids b ON i.id = b.id WHERE b.n = 1
        """,
        "lookup_compact": """
            SELECT i.payload FROM compact_ids i
            JOIN benchmark_ids b ON i.id = b.compact_id WHERE b.n = 1
        """,
        "interop_compact": """
            SELECT i.payload FROM compact_ids i
            JOIN benchmark_ids b ON i.id = b.id WHERE b.n = 1
        """,
        "input_native": """
            SELECT payload FROM native_ids
            WHERE id = (SELECT native_text::uuid FROM benchmark_inputs WHERE n = 1)
        """,
        "input_compact": """
            SELECT payload FROM compact_ids
            WHERE id = (SELECT compact_text::compact_uuid FROM benchmark_inputs WHERE n = 1)
        """,
        "output_native": "SELECT id FROM native_ids WHERE n BETWEEN 1 AND 100 ORDER BY n",
        "output_compact": "SELECT id FROM compact_ids WHERE n BETWEEN 1 AND 100 ORDER BY n",
        "range_native": """
            SELECT count(*) FROM (
                SELECT id FROM native_ids
                WHERE id >= (SELECT id FROM benchmark_ids WHERE n = 1)
                ORDER BY id LIMIT 100
            ) selected
        """,
        "range_compact": """
            SELECT count(*) FROM (
                SELECT id FROM compact_ids
                WHERE id >= (SELECT compact_id FROM benchmark_ids WHERE n = 1)
                ORDER BY id LIMIT 100
            ) selected
        """,
    }
    with psycopg.connect(**connection) as db:
        return {
            name: db.execute(f"EXPLAIN (FORMAT JSON, COSTS FALSE) {query}").fetchone()[
                0
            ][0]["Plan"]
            for name, query in queries.items()
        }


def plan_nodes(plan):
    return [plan["Node Type"]] + [
        node for child in plan.get("Plans", []) for node in plan_nodes(child)
    ]


def validate_plan_shapes(plans):
    for native, compact in (
        ("lookup_native", "lookup_compact"),
        ("input_native", "input_compact"),
        ("output_native", "output_compact"),
        ("range_native", "range_compact"),
    ):
        if plan_nodes(plans[native]) != plan_nodes(plans[compact]):
            raise RuntimeError(
                f"incomparable plans for {native} and {compact}: "
                f"{plan_nodes(plans[native])} != {plan_nodes(plans[compact])}"
            )


def parse_pgbench(output):
    latency = re.search(r"latency average = ([0-9.]+) ms", output)
    throughput = re.findall(r"tps = ([0-9.]+)", output)
    transactions = re.search(
        r"number of transactions actually processed: (\d+)", output
    )
    failures = re.search(r"number of failed transactions: (\d+)", output)
    if not latency or not throughput or not transactions:
        raise RuntimeError(f"could not parse pgbench output:\n{output}")
    return {
        "latency_ms": float(latency.group(1)),
        "tps": float(throughput[-1]),
        "transactions": int(transactions.group(1)),
        "failures": int(failures.group(1)) if failures else 0,
    }


def run_pgbench(container, args, workload, variant, duration):
    if workload == "insert":
        table = f"{variant}_writes"
        truncated = container.exec_run(
            ["psql", "-U", "postgres", "-c", f"TRUNCATE {table}"]
        )
        if truncated.exit_code:
            raise RuntimeError(truncated.output.decode())
    command = [
        "pgbench",
        "-U",
        "postgres",
        "-n",
        "-M",
        "prepared",
        "-c",
        str(args.clients),
        "-j",
        str(args.jobs),
        "-T",
        str(duration),
        "-D",
        f"row_count={args.rows}",
        "-D",
        f"output_max={args.rows - 99}",
        "-f",
        f"/benchmark/sql/{workload}_{variant}.sql",
        "postgres",
    ]
    result = container.exec_run(command)
    output = result.output.decode()
    if result.exit_code:
        raise RuntimeError(output)
    parsed = parse_pgbench(output)
    if parsed["failures"]:
        raise RuntimeError(output)
    return parsed


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def paired_ratio(samples, metric, seed):
    pairs = [
        (sample["compact"][metric], sample["native"][metric]) for sample in samples
    ]
    logs = [math.log(compact / native) for compact, native in pairs]
    estimate = math.exp(statistics.mean(logs))
    rng = random.Random(seed)
    bootstrapped = []
    for _ in range(10_000):
        bootstrapped.append(
            math.exp(statistics.mean(rng.choice(logs) for _ in range(len(logs))))
        )
    native_geomean = statistics.geometric_mean(native for _, native in pairs)
    compact_geomean = statistics.geometric_mean(compact for compact, _ in pairs)
    return {
        "compact_over_native": estimate,
        "percent_change": (estimate - 1) * 100,
        "ci95": [percentile(bootstrapped, 0.025), percentile(bootstrapped, 0.975)],
        "native_geomean": native_geomean,
        "compact_geomean": compact_geomean,
        "absolute_change": compact_geomean - native_geomean,
    }


def summarize(raw, seed):
    return {
        workload: {
            "latency_ms": paired_ratio(samples, "latency_ms", seed + index * 2),
            "tps": paired_ratio(samples, "tps", seed + index * 2 + 1),
        }
        for index, (workload, samples) in enumerate(raw.items())
    }


def markdown(report):
    lines = [
        "# compact_uuid benchmark results",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Configuration",
        "",
        f"- Rows: {report['configuration']['rows']:,}",
        f"- Paired repetitions: {report['configuration']['repetitions']}",
        f"- Duration per variant: {report['configuration']['duration']} seconds",
        f"- pgbench clients/workers: {report['configuration']['clients']}/{report['configuration']['jobs']}",
        f"- Host: `{report['environment']['host']}` (`{report['environment']['architecture']}`)",
        f"- Container CPUs: {report['environment']['container_cpus']}",
        f"- Container memory limit: `{report['environment']['container_memory_limit']}`",
        f"- PostgreSQL: `{report['environment']['postgres']}`",
        "",
        "## Paired workload results",
        "",
        "| Workload | Native latency | Compact latency | Absolute delta | Latency delta (95% CI) | Throughput delta (95% CI) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for workload, result in report["summary"].items():
        latency = result["latency_ms"]
        throughput = result["tps"]
        latency_ci = latency["ci95"]
        throughput_ci = throughput["ci95"]
        lines.append(
            f"| {workload} | {latency['native_geomean']:.4f} ms | "
            f"{latency['compact_geomean']:.4f} ms | {latency['absolute_change'] * 1000:+.2f} µs | "
            f"{latency['percent_change']:+.2f}% "
            f"({(latency_ci[0] - 1) * 100:+.2f}%–{(latency_ci[1] - 1) * 100:+.2f}%) | "
            f"{throughput['percent_change']:+.2f}% "
            f"({(throughput_ci[0] - 1) * 100:+.2f}%–{(throughput_ci[1] - 1) * 100:+.2f}%) |"
        )
    static = report["static"]
    lines.extend(
        [
            "",
            "## Static measurements",
            "",
            "| Measurement | Native UUID | compact_uuid |",
            "| --- | ---: | ---: |",
            f"| Datum size | {float(static['native_datum_bytes']):.0f} B | {float(static['compact_datum_bytes']):.0f} B |",
            f"| Text length | {float(static['native_text_chars']):.0f} chars | {float(static['compact_text_chars']):.0f} chars |",
            f"| Heap size | {static['native_heap_bytes']:,} B | {static['compact_heap_bytes']:,} B |",
            f"| Primary index size | {static['native_primary_index_bytes']:,} B | {static['compact_primary_index_bytes']:,} B |",
            f"| Total relation size | {static['native_total_bytes']:,} B | {static['compact_total_bytes']:,} B |",
            "",
            "Ratios are paired compact/native geometric means. Lower latency and higher throughput are better.",
        ]
    )
    return "\n".join(lines) + "\n"


def benchmark(args, postgres):
    connection = {
        "host": postgres.get_container_host_ip(),
        "port": int(postgres.get_exposed_port(5432)),
        "user": postgres.username,
        "password": postgres.password,
        "dbname": postgres.dbname,
    }
    setup_database(connection, args.rows)
    static = static_measurements(connection)
    plans = query_plans(connection)
    validate_plan_shapes(plans)
    container = postgres.get_wrapped_container()
    rng = random.Random(args.seed)
    raw = {workload: [] for workload in WORKLOADS}
    warmup_duration = min(3, args.duration)

    for workload in WORKLOADS:
        for variant in ("native", "compact"):
            run_pgbench(container, args, workload, variant, warmup_duration)
        for repetition in range(args.repetitions):
            variants = ["native", "compact"]
            rng.shuffle(variants)
            sample = {"repetition": repetition + 1, "order": variants.copy()}
            for variant in variants:
                sample[variant] = run_pgbench(
                    container, args, workload, variant, args.duration
                )
            raw[workload].append(sample)
            print(
                f"{workload} {repetition + 1}/{args.repetitions}: "
                f"native={sample['native']['latency_ms']:.4f} ms, "
                f"compact={sample['compact']['latency_ms']:.4f} ms",
                flush=True,
            )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "configuration": vars(args),
        "environment": {
            "host": platform.platform(),
            "architecture": platform.machine(),
            "postgres": static.pop("postgres_version"),
            "container_cpus": container.exec_run(["nproc"]).output.decode().strip(),
            "container_memory_limit": container.exec_run(
                [
                    "sh",
                    "-c",
                    "cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unknown",
                ]
            )
            .output.decode()
            .strip(),
        },
        "static": static,
        "summary": summarize(raw, args.seed),
        "plans": plans,
        "raw": raw,
    }


def main():
    args = arguments()
    image_context = (
        DockerImage(
            path=ROOT, dockerfile_path="Dockerfile", tag=args.image, clean_up=False
        )
        if not args.skip_build
        else nullcontext()
    )
    with image_context:
        with PostgresContainer(
            args.image,
            username="postgres",
            password="postgres",
            dbname="postgres",
            driver=None,
        ) as postgres:
            report = benchmark(args, postgres)

    results = ROOT / "benchmark/results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "latest.json").write_text(json.dumps(report, indent=2) + "\n")
    rendered = markdown(report)
    (results / "latest.md").write_text(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
