#!/usr/bin/env python2

##########################################################################
#
#   Generate quicklook images 
#
#   2022-04-14  Todd Valentic
#               Initial implementation
#
##########################################################################

from Transport import ProcessClient
from Transport.Util import PatternTemplate 
from sqlalchemy import desc

import sys
import schedule
import commands 
import fnmatch
import ConfigParser
import datetime
import commands

import model

class DateTracker:

    def __init__(self, filename, log):
        self.filename = filename
        self.log = log

        self.load()

    def load(self):
        self.tracker = ConfigParser.ConfigParser()
        self.tracker.read(self.filename)

    def save(self):
        with open(self.filename,'w') as f:
            self.tracker.write(f)

    def get_section(self, camera):

        station = camera.station.name
        instrument = camera.instrument.name
        section = '%s.%s' % (station, instrument)

        return section

    def get(self, camera): 

        section = self.get_section(camera) 

        if self.tracker.has_section(section):
            timestr = self.tracker.get(section, 'timestamp')
            timestamp = datetime.datetime.strptime(timestr,'%Y-%m-%d')
            count = self.tracker.getint(section, 'count')
        else:
            timestamp = None
            count = 0

        return timestamp, count

    def put(self, camera, timestamp, count):
        
        section = self.get_section(camera) 

        if not self.tracker.has_section(section):
            self.tracker.add_section(section)

        self.tracker.set(section, 'timestamp', str(timestamp.date()))
        self.tracker.set(section, 'count', str(count))

        self.save()

class ProcessRaw (ProcessClient):

    def __init__(self, argv):
        ProcessClient.__init__(self,argv)

        try:
            self.init()
        except:
            self.log.exception('Error')

    def init(self):

        self.scheduler      = schedule.Scheduler()
        self.tracker        = DateTracker('tracker.ini', self.log)
        self.schedule_at    = self.get('schedule.at','17:00:00')
        self.movie_cmd      = self.get('task.cmd')
        self.formats        = self.getList('formats','mp4')
        self.exitOnError    = self.getboolean('exitOnError',False)
        self.runAtStart     = self.getboolean('runAtStart',False)

        self.replaceStation     = PatternTemplate('station')
        self.replaceInstrument  = PatternTemplate('instrument')
        self.replaceFilelist    = PatternTemplate('filelist')
        self.replaceExt         = PatternTemplate('ext')

        self.replaceFilelist.setValue('filelist')

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

    def make_movie(self, camera, timestamp, ext):
        filelist = self.get_file_list(camera, timestamp) 

        with open('filelist','w') as f:
            f.write('\n'.join(filelist))

        cmd = self.replaceFilelist(self.movie_cmd) 
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
            return False

        self.tracker.put(camera, timestamp, len(filelist))

        return True

    def make_movies(self, camera, timestamp, formats):
        
        for ext in formats:
            self.log.info('      %s' % ext)
            if not self.make_movie(camera, timestamp, ext):
                return False

        return True

    def process_camera(self, camera):

        lasttime, lastcount = self.tracker.get(camera)
        timestamp = None

        if not lasttime:
            timestamp = self.get_first_image(camera).timestamp
            self.log.debug('No history, start with %s' % timestamp.date())
        else:
            lastlist = self.get_file_list(camera, lasttime) 

            if len(lastlist) != lastcount:
                self.log.debug('Need to reprocess %s. Image count differs (%d vs %d)' % \
                    (lasttime, lastcount, len(lastlist)))
                timestamp = lasttime
            else:
                image = self.find_next_image(camera, lasttime)
                if image:
                    self.log.debug('Next time is %s' % image.timestamp.date())
                    timestamp = image.timestamp

        if not timestamp:
            # No more images to process
            return False

        self.log.info('  - %s %s %s' % \
            (camera.station.name, camera.instrument.name, timestamp.date()))

        if not self.make_movies(camera, timestamp, self.formats):
            if self.exitOnError:
                self.abort('Problem detected creating movie. Stopping')

        return True 

    def process(self):

        self.log.info('Processing start')

        for camera in model.StationInstrument.query.all():
            while self.process_camera(camera) and self.running:
                pass
            if not self.running:
                break

        self.log.info('Processing finished')

    def schedule_task(self, at, cmd):

        self.log.info('Run task at %s' % at)

        if fnmatch.fnmatch(at, ':??'):
            self.scheduler.every(1).minutes.at(at).do(cmd)
        elif fnmatch.fnmatch(at, '??:??'):
                self.scheduler.every(1).hours.at(at).do(cmd)
        elif fnmatch.fnmatch(at, '??:??:??'):
            self.scheduler.every(1).day.at(at).do(cmd)

    def run(self):

        self.log.info('Running')

        if self.runAtStart:
            self.process()

        self.schedule_task(self.schedule_at, self.process)

        while self.wait(1):
            try:
                self.scheduler.run_pending()
            except:
                self.log.exception('Error detected')

        self.log.info('Exiting')

if __name__ == '__main__':
    ProcessRaw(sys.argv).run()

