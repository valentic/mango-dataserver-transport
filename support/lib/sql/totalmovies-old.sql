WITH summary as (

    SELECT
        station.name as station,
        instrument.name as instrument,
        min(pd.timestamp::date) startdate, 
        max(pd.timestamp::date) lastdate, 
        max(pd.timestamp::date) - min(pd.timestamp::date) + 1 totaldays,
        count(distinct pd.timestamp::date) as nummovies
    FROM
        stationinstrument
        JOIN
            station on station.id = stationinstrument.station_id
        JOIN
            instrument on instrument.id = stationinstrument.instrument_id
        JOIN
            system_model on system_model.id = station.model_id
        JOIN
            processed_data as pd on pd.stationinstrument_id = stationinstrument.id 
        JOIN 
            processed_product on processed_product.id = pd.product_id
    WHERE
        system_model.name = 'mcs'
        AND
        processed_product.name = 'quicklook'
        AND
        pd.timestamp < '2021-08-10'
    GROUP BY
        station, instrument
)


SELECT
    station as "Station",
    instrument as "Instrument",
    startdate as "Start Date",
    lastdate as "Last Date", 
    totaldays as "Total Days",
    format('%s %%', to_char((nummovies::real / totaldays)*100, '999')) as "Uptime",
    nummovies as "Num Movies"
FROM
    summary 
ORDER BY
    station, instrument
