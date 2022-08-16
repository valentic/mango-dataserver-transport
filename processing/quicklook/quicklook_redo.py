#!/usr/bin/env python2

##########################################################################
#
#   Reprocess quicklook images 
#
#   The input file format is a CSV file with the first line being headers:
#
#   station, instrument, timestamp
#   cfs, greenline, 2021-10-12
#   ...
#
#   station is the station code (lowercase)
#   instrument is the camera name (greenline | redline)
#   timestamp is the date in the format YYYY-MM-DD
#
#   2022-06-29  Todd Valentic
#               Initial implementation
#
##########################################################################

from quicklook_base import QuicklookBase
from Transport import NewsPollMixin
from Transport import NewsTool

import sys
import pytz
import csv
import datetime
import model

class QuicklookReprocess (QuicklookBase, NewsPollMixin):

    def __init__(self, argv):
        QuicklookBase.__init__(self, argv)
        NewsPollMixin.__init__(self, callback=self.process)

    def process_camera(self, camera, timestamp):

        self.log.info('  - %s %s %s' % \
            (camera.station.name, camera.instrument.name, timestamp.date()))

        self.make_movies(camera, timestamp, self.formats)

    def get_station(self, name):
        return model.Station.query.filter_by(name=name).first()

    def get_instrument(self, name):
        return model.Instrument.query.filter_by(name=name).first()

    def get_stationinstrument(self, station_name, instrument_name):
        station = self.get_station(station_name)
        instrument = self.get_instrument(instrument_name)

        if not station or not instrument:   
            return None

        return model.StationInstrument.query.filter_by(
            station_id=station.id,
            instrument_id=instrument.id
            ).first()
        
    def process_file(self, filename):

        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:

                camera = self.get_stationinstrument(row['station'], row['instrument']) 
                timestamp = datetime.datetime.strptime(row['timestamp'], '%Y-%m-%d')
                timestamp = timestamp.replace(tzinfo=pytz.utc)

                self.process_camera(camera, timestamp)

                if not self.running:
                    break

    def process(self, message):

        self.log.info('Processing start')

        filenames = NewsTool.saveFiles(message)

        for filename in filenames:
            self.process_file(filename)

        self.log.info('Processing finished')

if __name__ == '__main__':
    QuicklookReprocess(sys.argv).run()

