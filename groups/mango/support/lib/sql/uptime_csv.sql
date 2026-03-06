COPY (
SELECT
    timestamp::date as day, 
    FORMAT('%s %s', station.name, instrument.name) as camera
FROM
    stationinstrument
    JOIN processed_data as pd on pd.stationinstrument_id = stationinstrument.id
    JOIN processed_product on processed_product.id = pd.product_id
    JOIN station on station.id = stationinstrument.station_id
    JOIN instrument on instrument.id = stationinstrument.instrument_id
WHERE
    processed_product.name = 'quicklook'
GROUP BY
    day, camera 
) TO STDOUT WITH CSV HEADER
