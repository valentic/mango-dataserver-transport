#!/usr/bin/env python

##########################################################################
#
#   Sync remote data products:
#
#       - FPI/Mango winds
#
#   2023-02-08  Todd Valentic
#               Initial implementation
#
#   2023-02-10  Todd Valentic
#               Refactor database/output file naming
#
#   2023-02-14  Todd Valentic
#               Add transcoding for webm
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

class DataFile:

    # TBD - expand to be a factory for multiple data products

    def __init__(self, entry):

        self.entry = entry

        self.src_modtime, self.src_filesize, self.src_filename = entry.split()

        # src filenames are in the form DASI_<date>_<prod>.mp4
        # <date> - YYYYmmdd
        # <prod> - green or red
        # Example: DASI_20230206_green.mp4

        pattern = ".*DASI_([0-9]+)_([a-z]+).mp4"
        namemap = dict(green='winds-greenline', red='winds-redline')

        datestr, namekey = re.match(pattern, self.src_filename).groups()

        self.timestamp = datefunc.strptime(datestr, '%Y%m%d', tzinfo=pytz.utc)
        self.product = self._lookup_product(namemap[namekey])

    def _lookup_product(self, name):
        match = dict(name=name)
        return model.FusionProduct.query.filter_by(**match).first()

    def _lookup_datafile(self, timestamp, product):
        match = dict(timestamp=timestamp, product_id=product.id)
        return model.FusionData.query.filter_by(**match).first()

    def is_valid(self):

        match = dict(
            timestamp = self.timestamp,
            product_id = self.product.id,
            src_filesize = self.src_filesize,
            src_filename = self.src_filename,
            src_modtime = self.src_modtime
            )

        instance = model.FusionData.query.filter_by(**match).first()

        return instance is not None

    def update_db(self):

        match = dict(   
            timestamp = self.timestamp,
            product_id = self.product.id,
            )

        instance = model.FusionData.query.filter_by(**match).first()

        if not instance:    
            instance = model.FusionData(**match)
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
        self.replaceProduct = PatternTemplate('product')

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

    def download(self, datafile):

        self.log.info('  downloading')
        
        cmd = self.replaceFilename(self.fetch_cmd, datafile.src_filename)

        status, output = commands.getstatusoutput(cmd)

        if status != 0:
            self.log.error('Problem downloading:')
            self.log.error('  cmd: %s' % cmd)
            self.log.error('  status: %s' % status)
            self.log.error('  output: %s' % output)

            raise IOError('Failed to download %s' % datafile.src_filename)

    def copy_to_archive(self, datafile):

        destname = datafile.timestamp.strftime(self.output_name)
        destname = self.replaceFilename(destname, os.path.basename(datafile.src_filename))
        destname = self.replaceProduct(destname, datafile.product.name)

        self.log.info('  copy to archive: %s' % destname)

        srcname = os.path.basename(datafile.src_filename)

        dirname = os.path.dirname(destname)

        if not os.path.exists(dirname):
            os.makedirs(dirname)

        shutil.copyfile(srcname, destname)

        self.transcode(destname)

        os.remove(srcname)

    def transcode(self, filename):

        if not filename.endswith('mp4'):
            return

        self.log.info('  transcode')

        destname = filename.replace('.mp4', '.webm')

        cmd = 'ffmpeg -y -hide_banner -loglevel error -i %s -c:v libvpx-vp9 -crf 30 -b:v 0 -b:a 128k -c:a libopus %s' % (filename, destname)

        status, output = commands.getstatusoutput(cmd)

        if status != 0:
            self.log.error('Error transcoding')
            self.log.error('cmd: %s' % cmd)
            self.log.error('status: %s' % status)
            self.log.error('output: %s' % output)
            if self.exit_on_error:
                raise IOError('Error transcribing')

    def process(self):

        status, output = commands.getstatusoutput(self.scan_cmd)
        self.log.debug('status: %s' % status)
        self.log.debug('output: %s' % output)

        new_checksum = hashlib.md5(output).hexdigest()

        if new_checksum == self.checksum:
            self.log.debug('No change detected')
            return

        # DEBUG - REMOVE ONCE FIXED
        try:
            output = output.split('\n')
        except:
            self.log.error('*** Problem splitting')
            self.log.error('output=%s' % output)
            raise 

        self.log.info('Checking %d files' % len(output))
    
        for entry in output:

            datafile = DataFile(entry)

            if not datafile.is_valid():
                self.log.info(datafile.src_filename)
                self.download(datafile)
                self.copy_to_archive(datafile)
                datafile.update_db()

            if not self.running:
                return 

        self.save_checksum(new_checksum)

    def run(self):
        self.log.info('Start')

        while self.wait(self.rate):
            try:
                self.process()
            except:
                # Needed because sometimes we pick up errors
                # in the remote database 
                model.rollback()

                self.log.exception('Problem processing')
                if self.exit_on_error:
                    break

        self.log.info('Stop')

if __name__ == '__main__':
    Fetcher(sys.argv).run() 

