with summary as (
    SELECT
        station,
        instrument,
        count(island) as numimages,
        min(timestamp) as firsttime,
        max(timestamp) as lasttime,
        max(timestamp) - min(timestamp) as duration,
        date_trunc('day', min(timestamp)) as firstday
    FROM
        image_islands
    WHERE
        station='mto' and instrument='redline'
    GROUP BY
        station, instrument, island
    ORDER BY
        station, instrument, island
)

SELECT
    *,
    firstday - lag(firstday,1,firstday-interval '1d') over (order by firstday) as gap
FROM    
    summary
