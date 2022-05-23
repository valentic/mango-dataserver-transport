#!/usr/bin/env python

import os
import sys
import datetime

import model
import pytz

if __name__ == '__main__':

    count=0

    with open(sys.argv[1]) as filelist:

        for filename in filelist: 

            filename = filename.strip()
            if not filename:
                continue

            parts = filename.split(os.path.sep)
            station = model.Station.query.filter_by(name=parts[5]).first()
            instrument = model.Instrument.query.filter_by(name=parts[6]).first()

            camera = model.StationInstrument.query.filter_by(
                station_id=station.id,
                instrument_id=instrument.id
                ).first()

            timestamp = datetime.datetime.strptime('%s %s' % (parts[8],parts[9]),'%Y %j')
            timestamp = timestamp.replace(tzinfo=pytz.utc)

            match = dict(timestamp=timestamp, stationinstrument_id=camera.id)

            movie = model.QuickLookMovie.query.filter_by(**match).first()

            if not movie:
                movie = model.QuickLookMovie(**match)
                model.add(movie)
                #print movie

            if count % 100 == 0:
                print count
            count += 1

    try:
        model.commit()
    except:
        model.rollback()



