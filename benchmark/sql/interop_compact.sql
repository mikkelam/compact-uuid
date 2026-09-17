\set n random(1, :row_count)
SELECT i.payload
FROM compact_ids AS i
JOIN benchmark_ids AS b ON i.id = b.id
WHERE b.n = :n;
