"""Exercise the installed extension in an isolated Testcontainers database."""

import asyncio
import base64
import json
from pathlib import Path
import uuid

import asyncpg
import psycopg
from psycopg.types import TypeInfo
from testcontainers.core.image import DockerImage
from testcontainers.community.postgres import PostgresContainer

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "compact-uuid:test"
EXAMPLE = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
COMPACT = "VQ6EAOKbQdSnFkRmVUQAAA"
results: dict[str, object] = {}


async def check_asyncpg(connection):
    db = await asyncpg.connect(**connection)
    try:
        result = await db.fetchval("SELECT $1::compact_uuid", COMPACT)
        assert result == COMPACT
        results["asyncpg_text"] = {"type": type(result).__name__, "value": result}
        assert (
            await db.fetchval(
                "SELECT native FROM samples WHERE compact = $1::uuid", EXAMPLE
            )
            == EXAMPLE
        )
        assert await db.fetchval("SELECT ARRAY[$1::compact_uuid, NULL]", COMPACT) == [
            COMPACT,
            None,
        ]
        await db.set_type_codec(
            "compact_uuid",
            schema="public",
            format="binary",
            encoder=lambda value: value.bytes,
            decoder=lambda value: uuid.UUID(bytes=value),
        )
        result = await db.fetchval("SELECT $1::compact_uuid", EXAMPLE)
        assert result == EXAMPLE
        results["asyncpg_binary_codec"] = str(result)
    finally:
        await db.close()


def check_interoperability(db):
    db.execute("CREATE INDEX samples_native_idx ON samples(native)")
    for condition, parameter in [
        ("compact = %s", EXAMPLE),
        ("%s = compact", EXAMPLE),
        ("native = %s::compact_uuid", COMPACT),
        ("%s::compact_uuid = native", COMPACT),
    ]:
        plan = db.execute(
            f"EXPLAIN (FORMAT JSON) SELECT * FROM samples WHERE {condition}",
            (parameter,),
        ).fetchone()[0][0]["Plan"]
        assert "Index" in plan["Node Type"], plan
        assert plan.get("Index Cond"), plan
    results["mixed_type_index_lookups"] = 4

    for op in ["=", "<>", "<", "<=", ">", ">="]:
        assert db.execute(
            f"SELECT bool_and((compact {op} %s::uuid) = (native {op} %s::uuid)) FROM samples",
            (EXAMPLE, EXAMPLE),
        ).fetchone()[0]
        assert db.execute(
            f"SELECT bool_and((%s::uuid {op} compact) = (%s::uuid {op} native)) FROM samples",
            (EXAMPLE, EXAMPLE),
        ).fetchone()[0]
    results["mixed_type_comparisons"] = 12

    # Force each join algorithm to exercise the operator family's support functions.
    for algorithm in ["hashjoin", "mergejoin", "nestloop"]:
        with db.transaction():
            for other in ["hashjoin", "mergejoin", "nestloop"]:
                db.execute(
                    f"SET LOCAL enable_{other} = {'on' if other == algorithm else 'off'}"
                )
            assert (
                db.execute(
                    "SELECT count(*) FROM samples a JOIN samples b ON a.compact = b.native"
                ).fetchone()[0]
                == 10001
            )
    results["mixed_type_join_algorithms"] = 3

    db.execute("CREATE TABLE hash_ids (id compact_uuid)")
    db.execute("INSERT INTO hash_ids SELECT compact FROM samples")
    db.execute("CREATE INDEX hash_ids_idx ON hash_ids USING hash(id)")
    db.execute("ANALYZE hash_ids")
    assert (
        db.execute("SELECT id FROM hash_ids WHERE id = %s", (EXAMPLE,)).fetchone()[0]
        == COMPACT
    )
    plan = db.execute(
        "EXPLAIN (FORMAT JSON) SELECT id FROM hash_ids WHERE id = %s", (EXAMPLE,)
    ).fetchone()[0][0]["Plan"]
    assert plan["Index Name"] == "hash_ids_idx", plan

    db.execute(
        "CREATE TABLE defaults (id compact_uuid PRIMARY KEY DEFAULT gen_random_uuid(), ids compact_uuid[])"
    )
    value = db.execute(
        "INSERT INTO defaults(ids) VALUES (ARRAY[%s::compact_uuid, NULL]) RETURNING id",
        (COMPACT,),
    ).fetchone()[0]
    assert len(value) == 22
    # PostgreSQL sends the array text correctly; psycopg needs array OID registration to expose a list.
    info = TypeInfo.fetch(db, "compact_uuid")
    info.register(db)
    assert db.execute("SELECT ids FROM defaults").fetchone()[0] == [COMPACT, None]
    assert db.execute(
        "SELECT NULL::compact_uuid, NULL::uuid = NULL::compact_uuid"
    ).fetchone() == (None, None)
    assert db.execute(
        "SELECT ARRAY[%s::uuid]::compact_uuid[]::uuid[]", (EXAMPLE,)
    ).fetchone()[0] == [EXAMPLE]
    results["defaults_nulls_arrays"] = True

    db.execute("CREATE TABLE migrating (id uuid PRIMARY KEY DEFAULT gen_random_uuid())")
    db.execute("INSERT INTO migrating VALUES (%s)", (EXAMPLE,))
    db.execute(
        "ALTER TABLE migrating ALTER COLUMN id TYPE compact_uuid USING id::compact_uuid"
    )
    assert db.execute("SELECT id FROM migrating").fetchone()[0] == COMPACT
    assert (
        len(
            db.execute("INSERT INTO migrating DEFAULT VALUES RETURNING id").fetchone()[
                0
            ]
        )
        == 22
    )
    db.execute("ALTER TABLE migrating ALTER COLUMN id TYPE uuid USING id::uuid")
    assert (
        db.execute(
            "SELECT count(*) FROM migrating WHERE id = %s", (EXAMPLE,)
        ).fetchone()[0]
        == 1
    )
    results["migration_both_directions_with_default_and_pk"] = True

    db.execute("CREATE TABLE native_parent (id uuid PRIMARY KEY)")
    db.execute("INSERT INTO native_parent VALUES (%s)", (EXAMPLE,))
    db.execute("CREATE TABLE compact_child (id compact_uuid REFERENCES native_parent)")
    db.execute("INSERT INTO compact_child VALUES (%s)", (COMPACT,))
    db.execute("CREATE TABLE native_child (id uuid REFERENCES samples(compact))")
    db.execute("INSERT INTO native_child VALUES (%s)", (EXAMPLE,))
    assert (
        db.execute(
            "SELECT count(*) FROM compact_child JOIN native_parent ON compact_child.id = native_parent.id"
        ).fetchone()[0]
        == 1
    )
    results["mixed_type_foreign_keys"] = True


def check_database(connection):
    with psycopg.connect(**connection, autocommit=True) as db:
        db.execute("CREATE EXTENSION compact_uuid")
        assert (
            db.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'compact_uuid'"
            ).fetchone()[0]
            == "0.1.0"
        )
        value = db.execute("SELECT %s::compact_uuid", (COMPACT,)).fetchone()[0]
        assert value == COMPACT
        results["psycopg_text"] = {"type": type(value).__name__, "value": value}
        assert (
            db.execute("SELECT %s::compact_uuid::uuid", (COMPACT,)).fetchone()[0]
            == EXAMPLE
        )
        assert (
            db.execute("SELECT %s::compact_uuid", (EXAMPLE,)).fetchone()[0] == COMPACT
        )

        with db.cursor(binary=True) as cursor:
            value = cursor.execute("SELECT %s::compact_uuid", (COMPACT,)).fetchone()[0]
            assert value == EXAMPLE.bytes
            results["psycopg_binary_default"] = {
                "type": type(value).__name__,
                "hex": value.hex(),
            }

        db.execute(
            "CREATE TABLE samples (native uuid NOT NULL, compact compact_uuid PRIMARY KEY)"
        )
        db.execute(
            "INSERT INTO samples SELECT u, u FROM (SELECT gen_random_uuid() u FROM generate_series(1,10000)) s"
        )
        db.execute("INSERT INTO samples VALUES (%s, %s)", (EXAMPLE, EXAMPLE))
        row = db.execute(
            "SELECT count(*), bool_and(native = compact::uuid), min(pg_column_size(native)), max(pg_column_size(compact)) FROM samples"
        ).fetchone()
        assert row == (10001, True, 16, 16), row
        results["storage_and_casts"] = dict(
            zip(["rows", "all_equal", "uuid_bytes", "compact_bytes"], row)
        )
        native_order = db.execute(
            "SELECT native FROM samples ORDER BY native"
        ).fetchall()
        compact_order = db.execute(
            "SELECT compact::uuid FROM samples ORDER BY compact"
        ).fetchall()
        assert native_order == compact_order
        results["uuid_ordering"] = True

        rows = db.execute("SELECT native, compact FROM samples").fetchall()
        assert all(
            base64.urlsafe_b64encode(u.bytes).decode().rstrip("=") == c for u, c in rows
        )
        assert db.execute(
            "SELECT bool_and(compact = compact::text::compact_uuid) FROM samples"
        ).fetchone()[0]
        results["base64_roundtrip"] = len(rows)
        for invalid in [
            COMPACT[:-1] + "B",
            COMPACT + "==",
            "////////T/+//////////w",
            "short",
        ]:
            try:
                db.execute("SELECT %s::compact_uuid", (invalid,))
            except psycopg.errors.InvalidTextRepresentation:
                pass
            else:
                raise AssertionError(f"accepted invalid input: {invalid}")
        results["invalid_inputs_rejected"] = 4

        db.execute("ANALYZE samples")
        plan = db.execute(
            "EXPLAIN (FORMAT JSON) SELECT * FROM samples WHERE compact = %s::compact_uuid",
            (COMPACT,),
        ).fetchone()[0][0]["Plan"]
        assert "Index" in plan["Node Type"], plan
        results["lookup_plan"] = plan["Node Type"]
        try:
            db.execute("INSERT INTO samples VALUES (%s, %s)", (EXAMPLE, COMPACT))
        except psycopg.errors.UniqueViolation:
            results["uniqueness"] = True
        else:
            raise AssertionError("duplicate accepted")

        db.execute(
            "CREATE TABLE children (parent compact_uuid REFERENCES samples(compact))"
        )
        db.execute("INSERT INTO children VALUES (%s)", (COMPACT,))
        try:
            db.execute("INSERT INTO children VALUES (%s)", (str(uuid.uuid4()),))
        except psycopg.errors.ForeignKeyViolation:
            results["foreign_key"] = True
        else:
            raise AssertionError("missing parent accepted")
        assert (
            db.execute(
                "SELECT count(*) FROM samples JOIN children ON compact = parent"
            ).fetchone()[0]
            == 1
        )
        assert (
            len(
                db.execute(
                    "SELECT compact, count(*) FROM samples GROUP BY compact"
                ).fetchall()
            )
            == 10001
        )
        results["join_and_group_by"] = True
        assert (
            db.execute(
                "SELECT native FROM samples WHERE compact = %s", (EXAMPLE,)
            ).fetchone()[0]
            == EXAMPLE
        )
        results["uuid_parameter_without_cast"] = "works"
        check_interoperability(db)
        results["json"] = db.execute(
            "SELECT json_build_object('id', %s::compact_uuid)", (COMPACT,)
        ).fetchone()[0]
        assert results["json"] == {"id": COMPACT}

        db.execute("CREATE TABLE restored (LIKE samples INCLUDING ALL)")
        with db.cursor() as cursor:
            with cursor.copy("COPY samples TO STDOUT (FORMAT BINARY)") as copy:
                payload = b"".join(bytes(block) for block in copy)
            with cursor.copy("COPY restored FROM STDIN (FORMAT BINARY)") as copy:
                copy.write(payload)
        assert (
            db.execute(
                "SELECT count(*) FROM restored WHERE native = compact::uuid"
            ).fetchone()[0]
            == 10001
        )
        results["binary_copy_roundtrip"] = 10001


def check_dump_restore(postgres, connection):
    container = postgres.get_wrapped_container()
    dumped = container.exec_run(
        [
            "sh",
            "-c",
            "pg_dump -U postgres --no-owner --no-privileges postgres > /tmp/compact_uuid.sql",
        ]
    )
    assert dumped.exit_code == 0, dumped.output.decode()
    inspected = container.exec_run(
        [
            "sh",
            "-c",
            "grep -F 'CREATE EXTENSION IF NOT EXISTS compact_uuid' /tmp/compact_uuid.sql",
        ]
    )
    assert inspected.exit_code == 0, inspected.output.decode()
    with psycopg.connect(**connection, autocommit=True) as db:
        db.execute("CREATE DATABASE dump_restored")
    restored = container.exec_run(
        [
            "psql",
            "-U",
            "postgres",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-d",
            "dump_restored",
            "-f",
            "/tmp/compact_uuid.sql",
        ]
    )
    assert restored.exit_code == 0, restored.output.decode()
    restored_connection = connection | {"dbname": "dump_restored"}
    with psycopg.connect(**restored_connection, autocommit=True) as db:
        assert (
            db.execute(
                "SELECT count(*) FROM samples WHERE native = compact"
            ).fetchone()[0]
            == 10001
        )
        assert (
            db.execute(
                "SELECT count(*) FROM compact_child JOIN native_parent ON compact_child.id = native_parent.id"
            ).fetchone()[0]
            == 1
        )
    results["pg_dump_restore"] = True


def check_extension_lifecycle(connection):
    with psycopg.connect(**connection, autocommit=True) as db:
        db.execute("CREATE DATABASE lifecycle")
    lifecycle_connection = connection | {"dbname": "lifecycle"}
    with psycopg.connect(**lifecycle_connection, autocommit=True) as db:
        query = "SELECT count(*) FROM pg_amop WHERE amopfamily IN (SELECT oid FROM pg_opfamily WHERE opfname = 'uuid_ops')"
        baseline = db.execute(query).fetchone()[0]
        db.execute("CREATE SCHEMA ids")
        db.execute("CREATE EXTENSION compact_uuid SCHEMA ids")
        db.execute("SET search_path = ids, public")
        assert (
            db.execute("SELECT %s::compact_uuid", (COMPACT,)).fetchone()[0] == COMPACT
        )
        db.execute("ALTER EXTENSION compact_uuid SET SCHEMA public")
        assert (
            db.execute("SELECT %s::public.compact_uuid", (COMPACT,)).fetchone()[0]
            == COMPACT
        )
        db.execute("DROP EXTENSION compact_uuid")
        assert db.execute(query).fetchone()[0] == baseline
        assert db.execute("SELECT %s::uuid = %s::uuid", (EXAMPLE, EXAMPLE)).fetchone()[
            0
        ]
        db.execute("CREATE EXTENSION compact_uuid SCHEMA public")
        results["schema_relocation_drop_reinstall"] = True


def test_compact_uuid():
    with DockerImage(
        path=ROOT, dockerfile_path="Dockerfile", tag=IMAGE, clean_up=False
    ):
        with PostgresContainer(
            IMAGE,
            username="postgres",
            password="postgres",
            dbname="postgres",
            driver=None,
        ) as postgres:
            connection = {
                "host": postgres.get_container_host_ip(),
                "port": int(postgres.get_exposed_port(5432)),
                "user": postgres.username,
                "password": postgres.password,
                "dbname": postgres.dbname,
            }
            check_database(connection)
            async_connection = {
                key: value for key, value in connection.items() if key != "dbname"
            }
            async_connection["database"] = connection["dbname"]
            asyncio.run(check_asyncpg(async_connection))
            check_dump_restore(postgres, connection)
            check_extension_lifecycle(connection)

        output = json.dumps(results, indent=2)
        print(output)
        (ROOT / "target/integration-results.json").write_text(output + "\n")
