#!/usr/bin/env python

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
#   2026-02-23  Todd Valentic
#               Update for Python 3 / DataTransport 3
#
##########################################################################

import csv
import datetime
import sys

from datatransport import NewsPoller, newstool

import model
from processing_base import ProcessingBase


class ProcessingRedo(ProcessingBase):
    def __init__(self, argv):
        ProcessingBase.__init__(self, argv)

    def init(self):
        ProcessingBase.init(self)

        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

    def process_camera(self, camera, timestamp):

        self.log.info(
            "  - %s %s %s",
            camera.station.name,
            camera.instrument.name,
            timestamp.date(),
        )

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
            station_id=station.id, instrument_id=instrument.id
        ).first()

    def process_file(self, filename):

        with filename.open(newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                station = row["station"]
                instrument = row["instrument"]
                timestamp = row["timestamp"]

                camera = self.get_stationinstrument(station, instrument)
                timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%d").replace(
                    tzinfo=datetime.UTC
                )

                self.process_camera(camera, timestamp)

                if not self.running:
                    break

    def process(self, message):

        self.log.info("Processing start")

        filenames = newstool.save_files(message)

        for filename in filenames:
            self.process_file(filename)

        self.log.info("Processing finished")


if __name__ == "__main__":
    ProcessingRedo(sys.argv).run()
