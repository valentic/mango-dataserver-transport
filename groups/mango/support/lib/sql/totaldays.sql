select
    station as "Station",
    instrument as "Instrument",
    datadays as "Data Days",
    totaldays as "Total Days",
    format('%s %%', to_char(uptime, '999')) as "Uptime",
    totalimages as "Total Images",
    format('%10s', pg_size_pretty(totalbytes)) as "Total Bytes",
    firstday as "First Day",
    lastday as "Last Day"
from 
    total_summary 
order by
    station, instrument
