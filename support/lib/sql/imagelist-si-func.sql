DROP FUNCTION imagelist;
CREATE OR REPLACE FUNCTION imagelist (
    _station varchar, 
    _instrument varchar,
    _targetday date 
)
RETURNS table (
    filename text 
    )
LANGUAGE plpgsql
AS $$
BEGIN

RETURN QUERY
SELECT
    --station.name as "station",
    --instrument.name as "instrument",
    --image.timestamp as "timestamp",
    CONCAT_WS('/',
        '/data/transport/mango/archive',
        station.name,
        instrument.name,
        to_char(image.timestamp,'YYYY/DDD/HH24'),
        'mango-'||station.name||'-'||instrument.name||'-'||
            to_char(image.timestamp,'YYYYMMDD-HH24MISS.png')
        ) as "filename"
FROM
    stationinstrument
    JOIN
        station on station.id = stationinstrument.station_id
    JOIN
        instrument on instrument.id = stationinstrument.instrument_id
    JOIN
        system_model on system_model.id=station.model_id
    JOIN
        status on status.id=station.status_id
    JOIN LATERAL (
        SELECT  
            station.name as "station_name",
            instrument.name as "instrument_name",
            imagegap.timestamp,
            grp
        FROM (
            SELECT 
                image.timestamp,
                sum( (image.timestamp >= prev_timestamp + interval '3 hours')::int ) over (order by image.timestamp) as grp
                FROM (SELECT image.*,
                             lag(image.timestamp, 1, image.timestamp) over (order by image.timestamp) as prev_timestamp
                      FROM image
                      WHERE stationinstrument_id=stationinstrument.id
                      ) image
                WHERE 
                    date_trunc('day', image.timestamp) between 
                        _targetday-interval '1 day' and _targetday
                ORDER BY image.timestamp 
            ) imagegap 
        ORDER BY
            grp desc
        ) as image ON TRUE
WHERE
    status.name='active'
    AND
    system_model.name='mcs'
    AND
    station.name=_station
    AND
    instrument.name=_instrument
ORDER BY
    station.name,instrument.name,image.timestamp
;

END;$$
