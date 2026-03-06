#!/usr/bin/env python

########################################################################
#
#   Store records into database.
#
#   Handles a generic class of data records. Match based on newsgroup
#   name.
#
#   2021-09-14  Todd Valentic
#               Initial implementation. Adapted for mango
#
#   2026-02-24  Todd Valentic
#               Updated for Python 3 / DataTransport 3
#
########################################################################

import fnmatch
import os
import sys

import artemis_store
from datatransport import NewsPoller, ProcessClient, newstool

DataProcessor = {
    "greenline": artemis_store.Store(),
    "redline": artemis_store.Store(),
}

DataFiles = {
    "greenline": ["*.dat.bz2"],
    "redline": ["*.dat.bz2"],
}


class StoreDB(ProcessClient):
    def __init__(self, args):
        ProcessClient.__init__(self, args)

    def init(self):
        ProcessClient.init(self)

        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

    def process(self, message):

        # newsgroup: transport.mango.station.<sitename>.outbound.<instrument>
        #                0       1      2         3         4         5
        # i.e. transport.mango.station.lwl.outbound.greenline

        newsgroup = message["Newsgroups"].split(".")
        servername = message["Xref"].split()[0]
        datatype = newsgroup[-1]
        location = newsgroup[1]
        sitename = newsgroup[3]
        store = DataProcessor[datatype]
        timestamp = newstool.message_date(message)

        self.log.info("%s - %s - %s", sitename, datatype, timestamp)

        opts = {
            "servername": servername,
            "datatype": datatype,
            "location": location,
            "sitename": sitename,
            "timestamp": timestamp,
        }

        for filename in newstool.save_files(message):
            if self.match_filename(filename, DataFiles[datatype]):
                store.process(filename, opts=opts)
            os.remove(filename)

    def match_filename(self, filename, patterns):

        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False


if __name__ == "__main__":
    StoreDB(sys.argv).run()
