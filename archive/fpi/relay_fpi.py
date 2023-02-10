#!/usr/bin/env python

##########################################################################
#
#   Fetch new FPI/MANGO movies 
#
#   2023-02-08  Todd Valentic
#               Initial implementation
#
##########################################################################

import hashlib
import os
import re
import sys
import shutil
import commands 

import pytz
import model

from Transport import ProcessClient
from Transport.Util import PatternTemplate
from Transport.Util import datefunc

class Movie:

    def __init__(self, entry):

        self.entry = entry

        self.src_modtime, self.src_filesize, self.src_filename = entry.split()

        # src filenames are in the form DASI_<date>_<inst>.mp4
        # <date> - YYYYmmdd
        # <inst> - green or red
        # Example: DASI_20230206_green.mp4

        pattern = ".*DASI_([0-9]+)_([a-z]+).mp4"
        namemap = dict(green='greenline', red='redline')

        datestr, namekey = re.match(pattern, self.src_filename).groups()

        self.timestamp = datefunc.strptime(datestr, '%Y%m%d', tzinfo=pytz.utc)
        self.instrument = self._lookup_instrument(namemap[namekey])

    def _lookup_instrument(self, name):
        return model.Instrument.query.filter_by(name=name).first()

    def _lookup_movie(self, timestamp, instrument):
        match = dict(timestamp=timestamp, instrument_id=instrument.id)
        movie = model.CombinedMovie.query.filter_by(**match).first()

        return movie

    def is_valid(self):

        match = dict(
            timestamp = self.timestamp,
            instrument_id = self.instrument.id,
            src_filesize = self.src_filesize,
            src_filename = self.src_filename,
            src_modtime = self.src_modtime
            )

        entry = model.CombinedMovie.query.filter_by(**match).first()

        return entry is not None

    def update_db(self):

        match = dict(   
            timestamp = self.timestamp,
            instrument_id = self.instrument.id,
            )

        instance = model.CombinedMovie.query.filter_by(**match).first()

        if not instance:    
            values = dict(
                timestamp = self.timestamp,
                instrument_id = self.instrument.id
                )
            instance = model.CombinedMovie(**values)
            model.add(instance)

        instance.src_filesize = self.src_filesize
        instance.src_filename = self.src_filename
        instance.src_modtime = self.src_modtime

        try:
            model.commit()
        except:
            model.rollback()
            raise

class Fetcher(ProcessClient):
    
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        try:    
            self.read_config()
        except:
            self.log.exception('Problem reading config')
            self.abort()

        self.checksumFile = 'checksum.dat'

        self.checksum = self.load_checksum()

    def read_config(self):

        self.scan_cmd = self.get('scan.cmd')
        self.fetch_cmd = self.get('fetch.cmd')
        self.output_name = self.get('output.name')

        self.rate = self.getRate('rate','5:00')
        self.exit_on_error = self.getboolean('exitOnError', False)

        self.replaceFilename = PatternTemplate('filename','.')
        self.replaceInstrument = PatternTemplate('instrument','.')

        self.log.info('Scan cmd: %s' % self.scan_cmd)
        self.log.info('Fetch cmd: %s' % self.fetch_cmd)

    def load_checksum(self):
        
        try: 
            with open(self.checksumFile) as f:
                return f.read() 
        except:
            return '' 

    def save_checksum(self, checksum):

        with open(self.checksumFile, 'w') as f:
            f.write(checksum)

        self.checksum = checksum

        self.log.info('Saving checksum')

    def download(self, movie):

        self.log.info('  downloading')
        
        cmd = self.replaceFilename(self.fetch_cmd, movie.src_filename)

        status, output = commands.getstatusoutput(cmd)

        if status != 0:
            self.log.error('Problem downloading:')
            self.log.error('  cmd: %s' % cmd)
            self.log.error('  status: %s' % status)
            self.log.error('  output: %s' % output)

            raise IOError('Failed to download %s' % movie.src_filename)

    def copy_to_archive(self, movie):

        destname = movie.timestamp.strftime(self.output_name)
        destname = self.replaceFilename(destname, os.path.basename(movie.src_filename))
        destname = self.replaceInstrument(destname, movie.instrument.name)

        self.log.info('  copy to archive: %s' % destname)

        srcname = os.path.basename(movie.src_filename)

        dirname = os.path.dirname(destname)

        if not os.path.exists(dirname):
            os.makedirs(dirname)

        shutil.copyfile(srcname, destname)

        os.remove(srcname)

    def process(self):

        status, output = commands.getstatusoutput(self.scan_cmd)
        self.log.debug('status: %s' % status)
        self.log.debug('output: %s' % output)

        new_checksum = hashlib.md5(output).hexdigest()

        if new_checksum == self.checksum:
            self.log.debug('No change detected')
            return

        output = output.split('\n')

        self.log.info('Checking %d files' % len(output))
    
        for entry in output:

            movie = Movie(entry)

            if not movie.is_valid():
                self.log.info(movie.src_filename)
                self.download(movie) 
                self.copy_to_archive(movie)
                movie.update_db()

            if not self.running:
                return 

        self.save_checksum(new_checksum)

    def run(self):
        self.log.info('Start')

        while self.wait(self.rate):
            try:
                self.process()
            except:
                self.log.exception('Problem processing')
                if self.exit_on_error:
                    break

        self.log.info('Stop')

if __name__ == '__main__':
    Fetcher(sys.argv).run() 
