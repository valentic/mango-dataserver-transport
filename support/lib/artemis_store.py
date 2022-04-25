#!/usr/bin/env python2

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
##########################################################################

from store_base import StoreBase

import model
import artemis_data

import sys
import os
import datetime
import pytz

class Store(StoreBase):

    def __init__(self, *pos, **kw):
        StoreBase.__init__(self, model, artemis_data, *pos, **kw)

    def getStation(self, name):

        match = {}
        match['name'] = name
        
        return self.lookup(match, model.Station)

    def getDevice(self, name):
        
        match = {}
        match['name'] = name

        return self.lookup(match, model.Device)

    def getInstrument(self, name):
        
        match = {}
        match['name'] = name

        return self.lookup(match, model.Instrument)

    def getStationInstrument(self, stationName, instrumentName):

        station = self.getStation(stationName)
        instrument = self.getInstrument(instrumentName)

        match = {}
        match['station_id'] = station.id
        match['instrument_id'] = instrument.id

        return self.lookup(match, model.StationInstrument)

    def getTimestamp(self, unixtime):
        
        timestamp = datetime.datetime.fromtimestamp(unixtime)
        timestamp = timestamp.replace(tzinfo=pytz.utc)

        return timestamp

    def updateRecord(self, snapshot, *pos, **kw):

        values = snapshot.metadata

        timestamp = self.getTimestamp(values['start_time'])
        stationinstrument = self.getStationInstrument(values['station'], values['instrument'])
        station = self.getStation(values['station'])
        device = self.getDevice(values['device_name'])
        instrument = self.getInstrument(values['instrument'])

        values['timestamp'] = timestamp 
        values['stationinstrument_id'] = stationinstrument.id
        values['device_id'] = device.id

        match = ['timestamp', 'stationinstrument_id']

        if not self.update(values, model.Image, primary_keys=match):
            self.reportError('Failed to update database')
            return False

        return True

if __name__ == '__main__':
    
    filename = sys.argv[1]

    store = Store(exitOnError=True)

    store.process(filename)


