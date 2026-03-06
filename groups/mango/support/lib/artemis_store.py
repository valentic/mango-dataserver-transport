#!/usr/bin/env python

##########################################################################
#
#   Store Artemis snapshots into database
#
#   2021-08-10  Todd Valentic
#               Initial implementation
#
#   2022-03-12  Todd Valentic
#               Use stationinstrument junction table
#
#   2026-02-23  Todd Valentic
#               Update for Python 3 / DataTransport 3
#
##########################################################################

import datetime
import sys

import artemis_data
import model
from store_base import StoreBase


class Store(StoreBase):
    def __init__(self, *pos, **kw):
        StoreBase.__init__(self, model, artemis_data, *pos, **kw)

    def get_station(self, name):

        match = {
            "name": name
        }

        return self.lookup(match, model.Station)

    def get_device(self, name):

        match = {
            "name": name
        }

        return self.lookup(match, model.Device)

    def get_instrument(self, name):

        match = {
            "name": name
        }

        return self.lookup(match, model.Instrument)

    def get_stationinstrument(self, station_name, instrument_name):

        station = self.get_station(station_name)
        instrument = self.get_instrument(instrument_name)

        match = {
            "station_id": station.id,
            "instrument_id": instrument.id
        }

        return self.lookup(match, model.StationInstrument)

    def get_timestamp(self, unixtime):

        return datetime.datetime.fromtimestamp(unixtime, tz=datetime.UTC)

    def update_record(self, snapshot, *pos, **kw):

        values = snapshot.metadata

        timestamp = self.get_timestamp(values["start_time"])
        stationinstrument = self.get_stationinstrument(
            values["station"], values["instrument"]
        )
        device = self.get_device(values["device_name"])

        values["timestamp"] = timestamp
        values["stationinstrument_id"] = stationinstrument.id
        values["device_id"] = device.id

        match = ["timestamp", "stationinstrument_id"]

        if not self.update(values, model.Image, primary_keys=match):
            self.reportError("Failed to update database")
            return False

        return True


if __name__ == "__main__":
    filename = sys.argv[1]

    store = Store(exit_on_error=True)

    store.process(filename)
