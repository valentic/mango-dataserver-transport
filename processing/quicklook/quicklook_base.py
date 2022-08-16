#!/usr/bin/env python2

##########################################################################
#
#   Base class for quicklook movie generators 
#
#   2022-06-29  Todd Valentic
#               Extracted from quicklook.py
#               Make parallel via multiprocessing 
#
##########################################################################

from Transport import ProcessClient
from Transport.Util import PatternTemplate 

import datetime
import commands
import tempfile
import os

import model
import subprocess
import multiprocessing
import shlex

def make_movie(cmd): 
    return subprocess.call(shlex.split(cmd))

def make_movie_2(cmd):
    status, output = commands.getstatusoutput(cmd)
    return (status, output)

class QuicklookBase(ProcessClient):

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        try:    
            self.init()
        except:
            self.log.exception('Error during init')
            self.abort()

    def init(self):

        self.movie_cmd          = self.get('task.cmd')
        self.formats            = self.getList('formats','mp4')
        self.exitOnError        = self.getboolean('exitOnError', False)

        self.replaceStation     = PatternTemplate('station')
        self.replaceInstrument  = PatternTemplate('instrument')
        self.replaceFilelist    = PatternTemplate('filelist')
        self.replaceExt         = PatternTemplate('ext')

        self.pool = multiprocessing.Pool(None)

    def log_elapsed(self, msg, starttime, indent=0):

        # Strip off microseconds

         seconds = (self.currentTime() - starttime).total_seconds()
         elapsed = datetime.timedelta(seconds=round(seconds)) 

         self.log.info('%s%s (%s)' % (' '*indent, msg, elapsed))

    def get_file_list(self, camera, date):

        station = camera.station.name
        instrument = camera.instrument.name

        engine = model.Base.metadata.bind
        sql = "select * from imagelist('%s','%s','%s');" % (station, instrument, date)

        filelist = [row[0] for row in engine.execute(sql).all()]

        return filelist

    def get_first_image(self, camera):
        
        query = model.Image.query.filter_by(stationinstrument_id=camera.id)
        query = query.order_by(model.Image.timestamp)
        image = query.first()

        return image 

    def find_next_image(self, camera, timestamp):

        Image = model.Image
        nextday = timestamp.date() + datetime.timedelta(days=1)
        query = Image.query.filter(Image.stationinstrument_id==camera.id, Image.timestamp>=nextday)
        query = query.order_by(Image.timestamp)
        image = query.first()

        return image

    def make_movie(self, camera, timestamp, ext, listname):

        cmd = self.replaceFilelist(self.movie_cmd, listname) 
        cmd = self.replaceStation(cmd, camera.station.name)
        cmd = self.replaceInstrument(cmd, camera.instrument.name)
        cmd = self.replaceExt(cmd, ext)
        cmd = timestamp.strftime(cmd)

        self.log.debug('Running %s' % cmd)

        status, output = commands.getstatusoutput(cmd)

        if status != 0:
            self.log.error('Problem running cmd')
            self.log.error('cmd: %s' % cmd)
            self.log.error('status: %s' % status)
            self.log.error('output: %s' % output)
            
            raise IOError('Failed to run command')

    def update_db(self, camera, timestamp):

        match = dict(timestamp=timestamp, stationinstrument_id=camera.id)
        movie = model.QuickLookMovie.query.filter_by(**match).first()

        if not movie:
            movie = model.QuickLookMovie(**match)
            model.add(movie)

            try:
                model.commit()
            except:
                self.log.exception('Problem updating database')
                model.rollback()
                raise

    def make_movies(self, camera, timestamp, formats):
        
        filelist = self.get_file_list(camera, timestamp) 

        with tempfile.NamedTemporaryFile(dir='.', delete=False) as f:
            f.write('\n'.join(filelist))

        cmd = self.replaceFilelist(self.movie_cmd, f.name) 
        cmd = self.replaceStation(cmd, camera.station.name)
        cmd = self.replaceInstrument(cmd, camera.instrument.name)
        cmd = timestamp.strftime(cmd)
                
        starttime = self.currentTime() 

        results = []

        try:
            tasks = [self.replaceExt(cmd, ext) for ext in formats]
            r = self.pool.map_async(make_movie_2, tasks, callback=results.append)
            r.wait()
        except:
            raise 
        finally: 
            os.remove(f.name)

        self.log_elapsed(', '.join(formats), starttime, indent=6)

        if sum([entry[0] for entry in results[0]]):
            self.log.info('results: %s' % results)
            raise IOError('Problem running movie commands: %s' % results)

        self.update_db(camera, timestamp)

        return len(filelist)
