DROP FUNCTION image_list;
CREATE OR REPLACE FUNCTION image_list (
    _station varchar, 
    _instrument varchar,
    _targetdate date 
)
RETURNS table (
    filename text 
    )
LANGUAGE plpgsql
AS $$
BEGIN

RETURN QUERY
SELECT
    CONCAT_WS('/',
        '/data/transport/mango/archive',
        _station,
        _instrument,
        'raw',
        to_char(images.timestamp,'YYYY/DDD/HH24'),
        'mango-'||_station||'-'||_instrument||'-'||
            to_char(images.timestamp,'YYYYMMDD-HH24MISS')||'.hdf5'
        ) as "filename"
FROM (
    SELECT 
        *
    FROM
        find_image_island(_station, _instrument, _targetdate)
    LIMIT 
        1
    ) as island
    LEFT JOIN LATERAL (
        SELECT
            *
        FROM 
            image
        WHERE
            image.stationinstrument_id = island.stationinstrument_id
            AND
            image.timestamp between island.starttime and island.endtime
    ) as images on TRUE
ORDER BY
    images.timestamp
;

END;$$
