\set n random(1, :row_count)
SELECT payload
FROM native_ids
WHERE id = (SELECT native_text::uuid FROM benchmark_inputs WHERE n = :n);
