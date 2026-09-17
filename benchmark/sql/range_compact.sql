\set n random(1, :row_count)
SELECT count(*)
FROM (
    SELECT id FROM compact_ids
    WHERE id >= (SELECT compact_id FROM benchmark_ids WHERE n = :n)
    ORDER BY id
    LIMIT 100
) AS selected;
