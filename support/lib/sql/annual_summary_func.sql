drop function if exists annual_summary(date, date);
create or replace function annual_summary(
    _start_date date,
    _end_date date
)

returns table (
    station varchar,
    instrument varchar,
    data_days bigint,
    total_images numeric,
    total_bytes text,
    first_day date,
    last_day date,
    deploy_day date,
    total_days integer,
    uptime text
)

as $$
begin

return query

    with 

    dailysummary as ( 
        select
            ii.station,
            ii.instrument,
            count(ii.island) as num_images,
            min(ii.timestamp) as first_timestamp,
            max(ii.timestamp) as last_timestamp
        from
            image_islands as ii
        group by
            ii.station, ii.instrument, ii.island
        order by
            ii.station, ii.instrument, ii.island
    ),

    datastart as (
        select
            ds.station,
            ds.instrument,
            min(ds.first_timestamp) as deploy_timestamp
        from 
            dailysummary as ds
        group by
            ds.station, ds.instrument
        order by
            ds.station, ds.instrument
    ),

    totalsummary as (
        select
            ds.station as station,
            ds.instrument as instrument,
            count(num_images) as data_days,
            sum(num_images) as total_images,
            min(first_timestamp::date) as first_day,
            max(last_timestamp::date) as last_day,
            min(deploy_timestamp::date) as deploy_day,
            _end_date - greatest(_start_date, min(deploy_timestamp::date)) as total_days
        from
            dailysummary as ds
        join
            datastart on datastart.station = ds.station and datastart.instrument = ds.instrument 
        where
            first_timestamp::date >= _start_date and first_timestamp < _end_date 
        group by
            ds.station, ds.instrument
    ),

    size_summary as ( 

        select
            station.name as station,
            instrument.name as instrument,
            sum(image.image_bytes) as total_bytes
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
            and
            image.timestamp >= _start_date and image.timestamp < _end_date 
        group by
            station, instrument
    ),

    summary as (

        select
            ts.station as station,
            ts.instrument as instrument,
            ts.data_days as data_days,
            ts.total_images as total_images,
            size_summary.total_bytes as total_bytes,
            ts.first_day,
            ts.last_day,
            ts.deploy_day,
            ts.total_days,
            (ts.data_days::real / ts.total_days * 100) as uptime
        from 
            totalsummary as ts
        join
            size_summary on size_summary.station = ts.station and size_summary.instrument = ts.instrument 
        order by
            ts.station, ts.instrument
    ) 

    select
        summary.station,
        summary.instrument,
        summary.data_days,
        summary.total_images,
        lpad(pg_size_pretty(summary.total_bytes), 7) as total_bytes,
        summary.first_day,
        summary.last_day,
        summary.deploy_day,
        summary.total_days,
        lpad(to_char(summary.uptime, 'fm999D0%'), 6) as uptime
    from summary
    union all
        select
            'Summary' as station,
            to_char(count(summary.instrument), 'fm99') as instrument,
            sum(summary.data_days)::integer,
            sum(summary.total_images)::numeric,
            lpad(pg_size_pretty(sum(summary.total_bytes)), 7) as total_bytes,
            NULL as first_day,
            NULL as last_day,
            NULL as deploy_day,
            sum(summary.total_days)::integer,
            lpad(to_char(avg(summary.uptime), 'fm999D0%'), 6) as uptime
        from summary

;

end;
$$ language plpgsql;
