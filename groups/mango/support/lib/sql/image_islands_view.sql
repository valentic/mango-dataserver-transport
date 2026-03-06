CREATE OR REPLACE VIEW image_islands AS

    SELECT
        station.name as station,
        instrument.name as instrument,
        timestamp,
        island
    FROM (
        stationinstrument
        JOIN
            station on station.id = stationinstrument.station_id
        JOIN
            instrument on instrument.id = stationinstrument.instrument_id
        JOIN
            system_model on system_model.id = station.model_id
        JOIN
            status on status.id = station.status_id
        LEFT JOIN LATERAL (
            SELECT
                timestamp,
                sum(gap) over (order by timestamp) as island
            FROM (
                SELECT
                    stationinstrument_id,
                    timestamp,
                    (timestamp - lag(timestamp,1,timestamp-interval '1d') over (order by timestamp) > interval '3h')::int as gap 
                FROM
                    image
                WHERE
                    stationinstrument_id=stationinstrument.id
                ORDER BY
                    timestamp
                ) as t1 
            GROUP BY
                timestamp,
                gap
            ) as islands on TRUE
        )
    WHERE
        status.name='active'
        AND
        system_model.name='mcs'

