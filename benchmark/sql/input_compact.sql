\set n random(1, :row_count)
SELECT payload
FROM compact_ids
WHERE id = (SELECT compact_text::compact_uuid FROM benchmark_inputs WHERE n = :n);
