\set n random(1, :output_max)
SELECT id
FROM native_ids
WHERE n BETWEEN :n AND :n + 99
ORDER BY n;
