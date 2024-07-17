-- 2024-07-15 TAV Remove constraint that station must be active
-- 2024-07-16 TAV Add status in return table

DROP FUNCTION image_islands_span;
CREATE OR REPLACE FUNCTION image_islands_span (
    _span_start timestamp with time zone,
    _span_end timestamp with time zone 
)

RETURNS TABLE (
    stationinstrument_id integer,
    station varchar,
    instrument varchar,
    "timestamp" timestamp with time zone,
    island bigint,
    status varchar
)

LANGUAGE plpgsql
AS $$
BEGIN

RETURN QUERY
    SELECT
        stationinstrument.id as stationinstrument_id,
        station.name as station,
        instrument.name as instrument,
        islands.timestamp as "timestamp",
        islands.island,
        status.name as status
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
                t1.timestamp,
                sum(gap) over (order by t1.timestamp) as island
            FROM (
                SELECT
                    image.stationinstrument_id,
                    image.timestamp,
                    (image.timestamp - lag(image.timestamp,1,image.timestamp-interval '1d') over (order by image.timestamp) > interval '3h')::int as gap 
                FROM
                    image
                WHERE
                    image.stationinstrument_id=stationinstrument.id
                    AND
                    image.timestamp between _span_start and _span_end 
                ORDER BY
                    image.timestamp
                ) as t1 
            GROUP BY
                t1.timestamp,
                gap
            ) as islands on TRUE
        )
    WHERE
        --status.name='active'
        --AND
        system_model.name='mcs'

;

END;$$
