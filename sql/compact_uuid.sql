CREATE TYPE compact_uuid;
CREATE FUNCTION compact_uuid_in(cstring) RETURNS compact_uuid
AS 'MODULE_PATHNAME', 'compact_uuid_in_wrapper' LANGUAGE c IMMUTABLE STRICT PARALLEL SAFE;
CREATE FUNCTION compact_uuid_out(compact_uuid) RETURNS cstring
AS 'MODULE_PATHNAME', 'compact_uuid_out_wrapper' LANGUAGE c IMMUTABLE STRICT PARALLEL SAFE;
CREATE FUNCTION compact_uuid_recv(internal) RETURNS compact_uuid
AS 'uuid_recv' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE FUNCTION compact_uuid_send(compact_uuid) RETURNS bytea
AS 'uuid_send' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE TYPE compact_uuid (
    INPUT = compact_uuid_in, OUTPUT = compact_uuid_out,
    RECEIVE = compact_uuid_recv, SEND = compact_uuid_send,
    INTERNALLENGTH = 16, ALIGNMENT = char, STORAGE = plain
);
CREATE CAST (uuid AS compact_uuid) WITHOUT FUNCTION AS ASSIGNMENT;
CREATE CAST (compact_uuid AS uuid) WITHOUT FUNCTION AS ASSIGNMENT;

-- All signatures share PostgreSQL UUID storage, ordering, and hash semantics.
CREATE FUNCTION compact_uuid_eq(compact_uuid, compact_uuid) RETURNS boolean
AS 'uuid_eq' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR = (LEFTARG = compact_uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_eq, COMMUTATOR = '=', NEGATOR = '<>',
    RESTRICT = eqsel, JOIN = eqjoinsel, HASHES, MERGES);
CREATE FUNCTION compact_uuid_ne(compact_uuid, compact_uuid) RETURNS boolean
AS 'uuid_ne' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR <> (LEFTARG = compact_uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_ne, COMMUTATOR = '<>', NEGATOR = '=',
    RESTRICT = neqsel, JOIN = neqjoinsel);
CREATE FUNCTION compact_uuid_lt(compact_uuid, compact_uuid) RETURNS boolean
AS 'uuid_lt' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR < (LEFTARG = compact_uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_lt, COMMUTATOR = '>', NEGATOR = '>=',
    RESTRICT = scalarltsel, JOIN = scalarltjoinsel);
CREATE FUNCTION compact_uuid_le(compact_uuid, compact_uuid) RETURNS boolean
AS 'uuid_le' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR <= (LEFTARG = compact_uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_le, COMMUTATOR = '>=', NEGATOR = '>',
    RESTRICT = scalarlesel, JOIN = scalarlejoinsel);
CREATE FUNCTION compact_uuid_gt(compact_uuid, compact_uuid) RETURNS boolean
AS 'uuid_gt' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR > (LEFTARG = compact_uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_gt, COMMUTATOR = '<', NEGATOR = '<=',
    RESTRICT = scalargtsel, JOIN = scalargtjoinsel);
CREATE FUNCTION compact_uuid_ge(compact_uuid, compact_uuid) RETURNS boolean
AS 'uuid_ge' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR >= (LEFTARG = compact_uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_ge, COMMUTATOR = '<=', NEGATOR = '<',
    RESTRICT = scalargesel, JOIN = scalargejoinsel);
CREATE FUNCTION compact_uuid_cmp(compact_uuid, compact_uuid) RETURNS integer
AS 'uuid_cmp' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;

CREATE FUNCTION compact_uuid_eq(compact_uuid, uuid) RETURNS boolean
AS 'uuid_eq' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR = (LEFTARG = compact_uuid, RIGHTARG = uuid,
    FUNCTION = compact_uuid_eq, COMMUTATOR = '=', NEGATOR = '<>',
    RESTRICT = eqsel, JOIN = eqjoinsel, HASHES, MERGES);
CREATE FUNCTION compact_uuid_ne(compact_uuid, uuid) RETURNS boolean
AS 'uuid_ne' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR <> (LEFTARG = compact_uuid, RIGHTARG = uuid,
    FUNCTION = compact_uuid_ne, COMMUTATOR = '<>', NEGATOR = '=',
    RESTRICT = neqsel, JOIN = neqjoinsel);
CREATE FUNCTION compact_uuid_lt(compact_uuid, uuid) RETURNS boolean
AS 'uuid_lt' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR < (LEFTARG = compact_uuid, RIGHTARG = uuid,
    FUNCTION = compact_uuid_lt, COMMUTATOR = '>', NEGATOR = '>=',
    RESTRICT = scalarltsel, JOIN = scalarltjoinsel);
CREATE FUNCTION compact_uuid_le(compact_uuid, uuid) RETURNS boolean
AS 'uuid_le' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR <= (LEFTARG = compact_uuid, RIGHTARG = uuid,
    FUNCTION = compact_uuid_le, COMMUTATOR = '>=', NEGATOR = '>',
    RESTRICT = scalarlesel, JOIN = scalarlejoinsel);
CREATE FUNCTION compact_uuid_gt(compact_uuid, uuid) RETURNS boolean
AS 'uuid_gt' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR > (LEFTARG = compact_uuid, RIGHTARG = uuid,
    FUNCTION = compact_uuid_gt, COMMUTATOR = '<', NEGATOR = '<=',
    RESTRICT = scalargtsel, JOIN = scalargtjoinsel);
CREATE FUNCTION compact_uuid_ge(compact_uuid, uuid) RETURNS boolean
AS 'uuid_ge' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR >= (LEFTARG = compact_uuid, RIGHTARG = uuid,
    FUNCTION = compact_uuid_ge, COMMUTATOR = '<=', NEGATOR = '<',
    RESTRICT = scalargesel, JOIN = scalargejoinsel);
CREATE FUNCTION compact_uuid_cmp(compact_uuid, uuid) RETURNS integer
AS 'uuid_cmp' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;

CREATE FUNCTION compact_uuid_eq(uuid, compact_uuid) RETURNS boolean
AS 'uuid_eq' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR = (LEFTARG = uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_eq, COMMUTATOR = '=', NEGATOR = '<>',
    RESTRICT = eqsel, JOIN = eqjoinsel, HASHES, MERGES);
CREATE FUNCTION compact_uuid_ne(uuid, compact_uuid) RETURNS boolean
AS 'uuid_ne' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR <> (LEFTARG = uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_ne, COMMUTATOR = '<>', NEGATOR = '=',
    RESTRICT = neqsel, JOIN = neqjoinsel);
CREATE FUNCTION compact_uuid_lt(uuid, compact_uuid) RETURNS boolean
AS 'uuid_lt' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR < (LEFTARG = uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_lt, COMMUTATOR = '>', NEGATOR = '>=',
    RESTRICT = scalarltsel, JOIN = scalarltjoinsel);
CREATE FUNCTION compact_uuid_le(uuid, compact_uuid) RETURNS boolean
AS 'uuid_le' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR <= (LEFTARG = uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_le, COMMUTATOR = '>=', NEGATOR = '>',
    RESTRICT = scalarlesel, JOIN = scalarlejoinsel);
CREATE FUNCTION compact_uuid_gt(uuid, compact_uuid) RETURNS boolean
AS 'uuid_gt' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR > (LEFTARG = uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_gt, COMMUTATOR = '<', NEGATOR = '<=',
    RESTRICT = scalargtsel, JOIN = scalargtjoinsel);
CREATE FUNCTION compact_uuid_ge(uuid, compact_uuid) RETURNS boolean
AS 'uuid_ge' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE OPERATOR >= (LEFTARG = uuid, RIGHTARG = compact_uuid,
    FUNCTION = compact_uuid_ge, COMMUTATOR = '<=', NEGATOR = '<',
    RESTRICT = scalargesel, JOIN = scalargejoinsel);
CREATE FUNCTION compact_uuid_cmp(uuid, compact_uuid) RETURNS integer
AS 'uuid_cmp' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;

CREATE FUNCTION compact_uuid_hash(compact_uuid) RETURNS integer
AS 'uuid_hash' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE FUNCTION compact_uuid_hash_extended(compact_uuid, bigint) RETURNS bigint
AS 'uuid_hash_extended' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;
CREATE FUNCTION compact_uuid_sortsupport(internal) RETURNS void
AS 'uuid_sortsupport' LANGUAGE internal IMMUTABLE STRICT PARALLEL SAFE;

-- Membership in UUID's families also enables mixed-type lookups on native UUID indexes.
CREATE OPERATOR CLASS compact_uuid_ops DEFAULT FOR TYPE compact_uuid
USING btree FAMILY pg_catalog.uuid_ops AS
    OPERATOR 1 <, OPERATOR 2 <=, OPERATOR 3 =, OPERATOR 4 >=, OPERATOR 5 >,
    FUNCTION 1 compact_uuid_cmp(compact_uuid, compact_uuid),
    FUNCTION 2 compact_uuid_sortsupport(internal);
CREATE OPERATOR CLASS compact_uuid_ops DEFAULT FOR TYPE compact_uuid
USING hash FAMILY pg_catalog.uuid_ops AS
    OPERATOR 1 =,
    FUNCTION 1 compact_uuid_hash(compact_uuid),
    FUNCTION 2 compact_uuid_hash_extended(compact_uuid, bigint);
ALTER OPERATOR FAMILY pg_catalog.uuid_ops USING btree ADD
    OPERATOR 1 < (compact_uuid, uuid),
    OPERATOR 2 <= (compact_uuid, uuid),
    OPERATOR 3 = (compact_uuid, uuid),
    OPERATOR 4 >= (compact_uuid, uuid),
    OPERATOR 5 > (compact_uuid, uuid),
    FUNCTION 1 (compact_uuid, uuid) compact_uuid_cmp(compact_uuid, uuid);
ALTER OPERATOR FAMILY pg_catalog.uuid_ops USING hash ADD
    OPERATOR 1 = (compact_uuid, uuid);
ALTER OPERATOR FAMILY pg_catalog.uuid_ops USING btree ADD
    OPERATOR 1 < (uuid, compact_uuid),
    OPERATOR 2 <= (uuid, compact_uuid),
    OPERATOR 3 = (uuid, compact_uuid),
    OPERATOR 4 >= (uuid, compact_uuid),
    OPERATOR 5 > (uuid, compact_uuid),
    FUNCTION 1 (uuid, compact_uuid) compact_uuid_cmp(uuid, compact_uuid);
ALTER OPERATOR FAMILY pg_catalog.uuid_ops USING hash ADD
    OPERATOR 1 = (uuid, compact_uuid);
COMMENT ON TYPE compact_uuid IS '128-bit UUID; canonical 22-character unpadded Base64url output';
