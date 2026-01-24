-- Migrate Documents Tags to Lowercase
UPDATE documents
SET
    tags = (
        SELECT jsonb_agg (DISTINCT lower(val))
        FROM jsonb_array_elements_text (tags) as val
    )
WHERE
    tags IS NOT NULL
    AND jsonb_array_length (tags) > 0;

-- Migrate Tag Statistics to Lowercase
-- 1. Create temporary aggregated data
CREATE TEMP
TABLE temp_tag_stats AS
SELECT lower(tag) as new_tag, SUM(count) as new_count
FROM tag_statistics
GROUP BY
    lower(tag);

-- 2. Clear existing stats
TRUNCATE TABLE tag_statistics;

-- 3. Insert aggregated stats
INSERT INTO
    tag_statistics (tag, count)
SELECT new_tag, new_count
FROM temp_tag_stats;

-- 4. Cleanup
DROP TABLE temp_tag_stats;