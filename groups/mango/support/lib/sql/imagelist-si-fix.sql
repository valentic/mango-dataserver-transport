-- Call as

WITH images as (
    SELECT
        station,
        instrument,
        timestamp,
        island
    FROM
        image_islands_span(date :'date' - interval '1d', date :'date' + interval '1d')
    WHERE
        station=:'station'
        AND
        instrument=:'instrument'
    ORDER BY 
        island, timestamp
)

SELECT
    --station.name as "station",
    --instrument.name as "instrument",
    --to_char(image.timestamp, 'YYYY-MM-DD HH24:MI:SS') as "timestamp",
    --grp,
    CONCAT_WS('/',
        '/data/transport/mango/archive',
        station,
        instrument,
        'raw',
        to_char(timestamp,'YYYY/DDD/HH24'),
        'mango-'||station||'-'||instrument||'-'||
            to_char(timestamp,'YYYYMMDD-HH24MISS')||'.hdf5'
        ) as "filename"
FROM    
    images
ORDER BY
    timestamp
