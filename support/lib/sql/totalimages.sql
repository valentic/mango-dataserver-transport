SELECT
    station.name as station,
    instrument.name as instrument,
    to_char(min(image.timestamp), 'YYYY-MM-DD') as "Start Date",
    to_char(max(image.timestamp), 'YYYY-MM-DD') as "Last Date",
    count(image.timestamp) as "Num Images",
    format('%10s', pg_size_pretty(sum(image.image_bytes))) as "Total Bytes"
FROM
    stationinstrument
    JOIN
        station on station.id = stationinstrument.station_id
    JOIN
        instrument on instrument.id = stationinstrument.instrument_id
    JOIN
        system_model on system_model.id = station.model_id
    JOIN
        image on image.stationinstrument_id = stationinstrument.id
WHERE
    system_model.name = 'mcs'
GROUP BY
    station, instrument
ORDER BY
    station, instrument
