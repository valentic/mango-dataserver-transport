-- Call as

SELECT
    station.name as "station",
    instrument.name as "instrument",
    to_char(timestamp, 'YYYY-MM-DD HH24:MI:SS') as "timestamp",
    CONCAT_WS('/',
        '/data/transport/mango/archive',
        station.name,
        instrument.name,
        to_char(timestamp,'YYYY/DDD/HH24'),
        'mango-'||station.name||'-'||instrument.name||'-'||
            to_char(timestamp,'YYYYMMDD-HH24MISS.png')
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
            timestamp,
            grp
        FROM (
            SELECT 
                image.timestamp,
                sum( (timestamp >= prev_timestamp + interval '3 hours')::int ) over (order by timestamp) as grp
                FROM (SELECT image.*,
                             lag(timestamp, 1, timestamp) over (order by timestamp) as prev_timestamp
                      FROM image
                      WHERE stationinstrument_id=stationinstrument.id
                      ) image
                WHERE 
                    date_trunc('day', timestamp) between 
                        (date :'targetday')-interval '1 day' and (date :'targetday')
                ORDER BY timestamp 
            ) imagegap 
        ORDER BY
            grp desc
        ) as image ON TRUE
WHERE
    status.name='active'
    AND
    system_model.name='mcs'
ORDER BY
    station.name,instrument.name,timestamp
