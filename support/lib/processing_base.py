#!/usr/bin/env python2

##########################################################################
#
#   Base class for site data processing
#
#   2023-02-27  Todd Valentic
#               Similar to quicklook processing 
#
#   2023-05-04  Todd Valentic
#               Cast timestamp -> date in database update
#
##########################################################################

from Transport import ProcessClient
from Transport.Util import PatternTemplate 

import datetime
import commands
import tempfile
import os

import model
import multiprocessing
import shlex

def processing_handler(cmd):
    status, output = commands.getstatusoutput(cmd)
    return (status, output)

class ProcessingBase(ProcessClient):

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        try:    
            self.init()
        except:
            self.log.exception('Error during init')
            self.abort()

    def init(self):

        self.task_cmd           = self.get('task.cmd')
        self.formats            = self.getList('formats','mp4')
        self.exitOnError        = self.getboolean('exitOnError', False)

        self.replaceStation     = PatternTemplate('station')
        self.replaceInstrument  = PatternTemplate('instrument')
        self.replaceProduct     = PatternTemplate('product')
        self.replaceFilelist    = PatternTemplate('filelist')
        self.replaceExt         = PatternTemplate('ext')

        self.pool = multiprocessing.Pool(None)

        self.product = self.get_product(self.get('product'))

    def log_elapsed(self, msg, starttime, indent=0):

        # Strip off microseconds

         seconds = (self.currentTime() - starttime).total_seconds()
         elapsed = datetime.timedelta(seconds=round(seconds)) 

         self.log.info('%s%s (%s)' % (' '*indent, msg, elapsed))

    def get_product(self, name):
        return model.ProcessedProduct.query.filter_by(name=name).first()

    def get_file_list(self, camera, date):

        station = camera.station.name
        instrument = camera.instrument.name

        engine = model.Base.metadata.bind
        sql = "select * from image_list('%s','%s','%s');" % (station, instrument, date)

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

    def update_db(self, camera, timestamp):

        match = dict(timestamp=timestamp.date(), 
                     stationinstrument_id=camera.id, 
                     product_id=self.product.id)

        instance = model.ProcessedData.query.filter_by(**match).first()

        if not instance:
            instance = model.ProcessedData(**match)
            model.add(instance)

            try:
                model.commit()
            except:
                self.log.exception('Problem updating database')
                model.rollback()
                raise

    def make_products(self, camera, timestamp, formats):
        
        filelist = self.get_file_list(camera, timestamp) 

        with tempfile.NamedTemporaryFile(dir='.', delete=False) as f:
            f.write('\n'.join(filelist))

        cmd = self.replaceFilelist(self.task_cmd, f.name) 
        cmd = self.replaceStation(cmd, camera.station.name)
        cmd = self.replaceInstrument(cmd, camera.instrument.name)
        cmd = self.replaceProduct(cmd, self.product.name)
        cmd = timestamp.strftime(cmd)
                
        starttime = self.currentTime() 

        results = []

        try:
            tasks = [self.replaceExt(cmd, ext) for ext in formats]
            r = self.pool.map_async(processing_handler, tasks, callback=results.append)
            r.wait()
        except:
            raise 
        finally: 
            os.remove(f.name)

        self.log_elapsed(', '.join(formats), starttime, indent=6)

        if sum([entry[0] for entry in results[0]]):
            self.log.info('results: %s' % results)
            raise IOError('Problem running processing command: %s' % results)

        self.update_db(camera, timestamp)

        return len(filelist)


