-- Call as

SELECT
    station.name as "Station",
    instrument.name as "Instrument",
    to_char(group_start, 'YYYY-MM-DD HH24:MI:SS') as "Start Time (UTC)",
    to_char(group_stop, 'YYYY-MM-DD HH24:MI:SS') as "Stop Time (UTC)",
    duration as "Duration",
    num_images as "Num Images"
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
    LEFT JOIN LATERAL (
        SELECT  
            grp,
            min(timestamp) as "group_start",
            max(timestamp) as "group_stop",
            count(timestamp) as "num_images",
            max(timestamp)-min(timestamp) as "duration"
        FROM (
            SELECT 
                image.timestamp,
                sum( (timestamp >= prev_timestamp + interval '3 hours')::int ) over (order by timestamp) as grp
                FROM (SELECT image.*,
                             lag(timestamp, 1, timestamp) over (order by timestamp) as prev_timestamp
                      FROM image
                      WHERE
                        stationinstrument_id=stationinstrument.id
                      ) image
                WHERE 
                    date_trunc('day', timestamp) between 
                        (date :'date')-interval '1 day' and (date :'date')
                ORDER BY timestamp 
            ) subimage 
        GROUP BY
            grp
        ORDER BY
            grp desc
        LIMIT 1
        ) as image ON TRUE
WHERE
    status.name='active'
    AND
    system_model.name='mcs'
ORDER BY
    station.name,instrument.name
