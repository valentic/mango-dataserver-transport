DROP FUNCTION find_image_island;
CREATE OR REPLACE FUNCTION find_image_island (
    _station varchar,
    _instrument varchar,
    _targetdate timestamp with time zone
)

RETURNS TABLE (
    stationinstrument_id integer,
    starttime timestamp with time zone,
    endtime timestamp with time zone,
    midtime date, 
    num_images bigint 
)

LANGUAGE plpgsql
AS $$
BEGIN

RETURN QUERY
    WITH islands as (
        SELECT
            span.stationinstrument_id,
            min(timestamp) as starttime,
            max(timestamp) as endtime,
            (min(timestamp) + (max(timestamp) - min(timestamp))/2)::date as midtime,
            count(timestamp) as num_images
        FROM
            image_islands_span(_targetdate - interval '2d', _targetdate + interval '2d') as span
        WHERE
            station=_station
            AND
            instrument=_instrument
        GROUP BY
            span.stationinstrument_id, island
    )

    SELECT
        *
    FROM    
        islands
    WHERE
        islands.midtime=_targetdate

;

END;$$
