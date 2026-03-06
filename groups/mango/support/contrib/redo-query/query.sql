COPY (
SELECT
    station.name as station,
    instrument.name as instrument,
    to_char(timestamp, 'YYYY-MM-DD') as timestamp
FROM
    processed_data pd
JOIN
    processed_product ON pd.product_id=processed_product.id
JOIN
    stationinstrument si ON pd.stationinstrument_id=si.id
JOIN
    station ON station.id=si.station_id
JOIN
    instrument ON instrument.id=si.instrument_id
WHERE
    processed_product.name='quicklook'
    AND
    station.name=:'station'
    AND
    instrument.name=:'instrument'
    AND
    timestamp BETWEEN :'startdate' AND :'enddate'
ORDER BY
    timestamp
) TO STDOUT CSV HEADER 
