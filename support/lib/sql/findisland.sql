-- Call as

WITH islands as (
    SELECT
        station,
        instrument,
        min(timestamp) as starttime,
        max(timestamp) as endtime,
        (min(timestamp) + (max(timestamp) - min(timestamp))/2)::date as midtime,
        count(timestamp) as num_images
    FROM
        image_islands_span(date :'date' - interval '2d', date :'date' + interval '2d')
    WHERE
        station=:'station'
        AND
        instrument=:'instrument'
    GROUP BY
        station, instrument, island
)

SELECT
    *
FROM    
    islands
WHERE
    midtime=date:'date'
