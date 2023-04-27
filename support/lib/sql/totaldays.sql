with dailysummary as (

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

    select
        station,
        instrument,
        count(numimages) as datadays,
        sum(numimages) as totalimages,
        min(firsttime::date) as firstday,
        max(lasttime::date) as lastday,
        max(lasttime::date) - min(firsttime::date) + 1 as totaldays 
    from 
        dailysummary
    group by
        station, instrument

), sizesummary as (

    select
        station.name as station,
        instrument.name as instrument,
        sum(image.image_bytes) as totalbytes
    from    
        stationinstrument
        join
            station on station.id = stationinstrument.station_id
        join
            instrument on instrument.id = stationinstrument.instrument_id
        join
            system_model on system_model.id = station.model_id
        join
            image on image.stationinstrument_id = stationinstrument.id
    where
        system_model.name = 'mcs'
    group by
        station, instrument
)

select
    ts.station as "Station",
    ts.instrument as "Instrument",
    datadays as "Data Days",
    totaldays as "Total Days",
    format('%s %%', to_char(datadays::real / totaldays * 100, '999')) as "Uptime",
    totalimages as "Total Images",
    format('%10s', pg_size_pretty(totalbytes)) as "Total Bytes",
    to_char(firstday, 'YYYY-MM-DD') as "First Day",
    to_char(lastday, 'YYYY-MM-DD') as "Last Day"
from 
    totalsummary as ts
    join
        sizesummary as ss on ss.station = ts.station and ss.instrument = ts.instrument
order by
    ts.station, ts.instrument
