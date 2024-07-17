-- Call as
-- 2024-07-15 TAV Filter on active stations (image_islands_span returns all now)

WITH summary as (
    SELECT
        station,
        instrument,
        status,
        min(timestamp) as starttime,
        max(timestamp) as stoptime,
        count(timestamp) as num_images
    FROM
        image_islands_span(now()-interval '1d', now())
    GROUP BY
        station, instrument, status, island
)

SELECT
    station as "Station",
    instrument as "Instrument",
    to_char(starttime, 'YYYY-MM-DD HH24:MI:SS') as "Start Time (UTC)",
    to_char(stoptime, 'YYYY-MM-DD HH24:MI:SS') as "Stop Time (UTC)",
    stoptime - starttime as "Duration",
    num_images as "Num Images"
FROM
    summary 
WHERE
    status = 'active'
ORDER BY
    station, instrument
