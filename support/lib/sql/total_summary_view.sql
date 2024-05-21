CREATE OR REPLACE VIEW total_summary AS

WITH dailysummary as (

    SELECT
        station,
        instrument,
        count(island) as numimages,
        min(timestamp) as firsttime,
        max(timestamp) as lasttime
    FROM
        image_islands
    GROUP BY
        station, instrument, island
    ORDER BY
        station, instrument, island

), totalsummary as (

    SELECT
        station,
        instrument,
        count(numimages) as datadays,
        sum(numimages) as totalimages,
        min(firsttime::date) as firstday,
        max(lasttime::date) as lastday,
        max(lasttime::date) - min(firsttime::date) + 1 as totaldays,
        CURRENT_DATE as today,
        CURRENT_DATE - min(firsttime::date) + 1 as totaldays_today
    FROM 
        dailysummary
    GROUP BY
        station, instrument

), sizesummary as (

    SELECT
        station.name as station,
        instrument.name as instrument,
        sum(image.image_bytes) as totalbytes
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
)

SELECT
    ts.station as station,
    ts.instrument as instrument, 
    datadays,
    totaldays,
    datadays::real / totaldays * 100 as uptime,
    totalimages, 
    totalbytes,
    firstday,
    lastday,
    totaldays_today,
    datadays::real / totaldays_today * 100 as uptime_today,
    today
from 
    totalsummary as ts
    join
        sizesummary as ss on ss.station = ts.station and ss.instrument = ts.instrument
order by
    ts.station, ts.instrument
