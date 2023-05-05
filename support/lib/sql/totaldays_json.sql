select json_agg(t) from (
select
    * 
from 
    total_summary 
order by
    station, instrument
) as t
