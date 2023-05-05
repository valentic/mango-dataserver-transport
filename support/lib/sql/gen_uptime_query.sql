-- Run once: CREATE EXTENSION IF NOT EXISTS tablefunc;

SELECT FORMAT (
    $outer$
    COPY (
        SELECT 
            "Date",
            %s
        FROM crosstab(
            $$
            WITH counts AS (

                SELECT
                    timestamp::date as date_bin,
                    stationinstrument_id,
                    count(*)
                FROM
                    stationinstrument
                    JOIN processed_data as pd on pd.stationinstrument_id = stationinstrument.id
                    JOIN processed_product on processed_product.id = pd.product_id
                WHERE
                    processed_product.name = 'quicklook'
                GROUP BY
                    date_bin, stationinstrument_id
            )
            SELECT
                series::date,
                stationinstrument_id,
                coalesce(counts.count, 0) as count
            FROM
                generate_series('2014-01-01'::date, 'now'::date, '1 day'::interval) series
            LEFT JOIN
                counts ON counts.date_bin = series
            ORDER BY
                series, stationinstrument_id 
            $$,
            $$select id from stationinstrument order by id$$ 
        ) AS ct ("Date" date, %s)
    ) TO STDOUT WITH CSV HEADER
    $outer$,
    string_agg(FORMAT('coalesce("%s", 0) as "%s"', station_instrument, station_instrument), ', '),
    string_agg(FORMAT('"%s" %s', station_instrument, 'int'), ', ')
)
FROM (
    SELECT
        FORMAT('%s %s', station.name, instrument.name) as station_instrument
    FROM
        stationinstrument
        JOIN station on station.id = stationinstrument.station_id
        JOIN instrument on instrument.id = stationinstrument.instrument_id
    ORDER BY
        stationinstrument.id 
) as t
