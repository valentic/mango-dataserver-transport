#!/usr/bin/env python2

##########################################################################
#
#   Reprocess data product 
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
#   2023-02-17  Todd Valentic
#               Refactor to handle general data products
#               Strip white space from fields in csv file
#
##########################################################################

from processing_base import ProcessingBase
from Transport import NewsPollMixin
from Transport import NewsTool

import sys
import pytz
import csv
import datetime
import model

class ProcessingRedo (ProcessingBase, NewsPollMixin):

    def __init__(self, argv):
        ProcessingBase.__init__(self, argv)
        NewsPollMixin.__init__(self, callback=self.process)

    def process_camera(self, camera, timestamp):

        self.log.info('  - %s %s %s' % \
            (camera.station.name, camera.instrument.name, timestamp.date()))

        self.make_products(camera, timestamp, self.formats)

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

            # Manually read first line and trim white space from field names.

            header = [h.strip() for h in csvfile.next().split(',')]
            reader = csv.DictReader(csvfile, fieldnames=header)

            for row in reader:

                station = row['station'].strip()
                instrument = row['instrument'].strip()
                timestamp = row['timestamp'].strip()

                camera = self.get_stationinstrument(station, instrument) 
                timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d')
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
    ProcessingRedo(sys.argv).run()

