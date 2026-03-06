SELECT
    station.name as "station_name",
    instrument.name as "instrument_name",
    to_char(last_image.timestamp, 'YYYY-MM-DD HH24:MI:SS') as "timestamp",
    last_image.serialnum,
    last_image.exposure_time, 
    to_char(last_image.ccd_temp, '99D9') as "ccd_temp"
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
            *
        FROM image
        WHERE image.stationinstrument_id=stationinstrument.id
        ORDER BY timestamp desc
        LIMIT 1) as last_image
        ON true
WHERE
    status.name='active'
    AND
    system_model.name='mcs'
ORDER BY
    station.name, instrument.name
