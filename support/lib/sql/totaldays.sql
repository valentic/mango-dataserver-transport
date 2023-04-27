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
        min(firsttime::date) as firstday,
        max(lasttime::date) as lastday,
        max(lasttime::date) - min(firsttime::date) + 1 as totaldays 
    from 
        dailysummary
    group by
        station, instrument
)

select
    station as "Station",
    instrument as "Instrument",
    datadays as "Data Days",
    totaldays as "Total Days",
    format('%s %%', to_char(datadays::real / totaldays * 100, '999')) as "Uptime",
    to_char(firstday, 'YYYY-MM-DD') as "First Day",
    to_char(lastday, 'YYYY-MM-DD') as "Last Day"
from 
    totalsummary
order by
    station, instrument
