-- Call as

SELECT
    --station.name as "station",
    --instrument.name as "instrument",
    --to_char(image.timestamp, 'YYYY-MM-DD HH24:MI:SS') as "timestamp",
    --grp,
    CONCAT_WS('/',
        '/data/transport/mango/archive',
        station.name,
        instrument.name,
        'raw',
        to_char(image.timestamp,'YYYY/DDD/HH24'),
        'mango-'||station.name||'-'||instrument.name||'-'||
            to_char(image.timestamp,'YYYYMMDD-HH24MISS')||'.hdf5'
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
            imagegap.timestamp as "timestamp",
            grp
        FROM (
            SELECT 
                image.timestamp,
                sum( (image.timestamp >= prev_timestamp + interval '3 hours')::int ) over (order by image.timestamp) as grp
                FROM (SELECT image.*,
                             lag(timestamp, 1, timestamp) over (order by timestamp) as prev_timestamp
                      FROM image
                      WHERE stationinstrument_id=stationinstrument.id
                      ) image
                WHERE 
                    date_trunc('day', timestamp) between 
                        (date :'date') and (date :'date')+interval '1 day'
                ORDER BY timestamp 
            ) imagegap 
        WHERE
            grp=1
        ORDER BY
            grp desc, timestamp
        ) as image ON TRUE
WHERE
    status.name='active'
    AND
    system_model.name='mcs'
    AND
    station.name=:'station'
    AND
    instrument.name=:'instrument'
ORDER BY
    station.name,instrument.name,image.timestamp
