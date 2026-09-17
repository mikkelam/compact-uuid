# PostgreSQL compatibility contract

`compact_uuid` targets PostgreSQL 18.6. Its on-disk and binary representation,
comparison ordering, hashing, and index behavior intentionally match native
`uuid`; only text input and output differ.

The PostgreSQL 18.6 sources are the reference for this contract:

| Contract | PostgreSQL source |
| --- | --- |
| 16-byte, pass-by-reference, char-aligned storage and binary I/O | [`pg_type.dat`](https://github.com/postgres/postgres/blob/REL_18_6/src/include/catalog/pg_type.dat) |
| Comparison, sorting, hashing, and binary send/receive implementations | [`uuid.c`](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/utils/adt/uuid.c) |
| B-tree and hash operator classes | [`pg_opclass.dat`](https://github.com/postgres/postgres/blob/REL_18_6/src/include/catalog/pg_opclass.dat) |
| Operator-family strategies | [`pg_amop.dat`](https://github.com/postgres/postgres/blob/REL_18_6/src/include/catalog/pg_amop.dat) |
| Operator-family support functions | [`pg_amproc.dat`](https://github.com/postgres/postgres/blob/REL_18_6/src/include/catalog/pg_amproc.dat) |
| Function properties such as leakproof comparisons | [`pg_proc.dat`](https://github.com/postgres/postgres/blob/REL_18_6/src/include/catalog/pg_proc.dat) |
| Native UUID regression behavior | [`uuid.sql`](https://github.com/postgres/postgres/blob/REL_18_6/src/test/regress/sql/uuid.sql) |

The integration suite checks the installed PostgreSQL catalogs rather than
parsing `sql/compact_uuid.sql`. It verifies type layout, binary I/O, binary
assignment casts, operator metadata, and every B-tree and hash family member.
It also exercises ordering, indexes, joins, uniqueness, foreign keys, arrays,
binary COPY, and dump/restore against native UUID values.

Because the extension calls PostgreSQL `internal` UUID functions, supporting a
new PostgreSQL major version requires reviewing these catalog and source
definitions and running the full integration suite against that version.
