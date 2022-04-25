#!/usr/bin/env python

#####################################################################
#
#   Store data into database
#
#   2020-10-14  Todd Valentic
#               Initial implementation
#
#####################################################################

import sys
import os

from sqlalchemy.orm import class_mapper

class StoreBase:

    def __init__(self, model, dataHandler, log=None, exitOnError=True):

        if not log:
            self.setupBasicLogger()
        else:
            self.log = log

        self.model = model
        self.dataHandler = dataHandler
        self.exitOnError = exitOnError

    def setupBasicLogger(self):

        import logging

        self.log = logging
        logging.basicConfig(level=logging.INFO)

    def reportError(self, msg):
        self.log.error('Filename: %s' % self.filename)
        if self.exitOnError:
            self.log.exception(msg)
            raise RuntimeError(msg)
        else:
            self.log.error(msg)

    def process(self,filename,opts=None,*pos,**kw):
        
        self.filename = filename

        try:
            snapshots = self.dataHandler.read(filename,opts=opts)
        except:
            self.reportError('Problem loading data')
            return False

        for snapshot in snapshots:
            self.updateRecord(snapshot,*pos,**kw)

        return True

    def updateRecord(self,snapshot,*pos,**kw):
        # Filled in by child class
        pass

    def lookup(self,match,table):
        instance = table.query.filter_by(**match).first()
        return instance

    def lookupOrAdd(self,match,table):
        instance = table.query.filter_by(**match).first()

        if not instance:
            self.log.info('Added %s: %s' % (table,match))
            instance = table(**match)
            self.model.add(instance)

            try:
                self.model.commit()
            except:
                self.model.rollback()
                self.log.error('Problem adding')
                self.log.info('  - instance: %s' % instance)
                self.log.info('  - match: %s' % match)
                raise

        return instance

    def update(self,data,table,primary_keys=None):

        attrs = table.__dict__.keys()
        values = dict((k,v) for k,v in data.items() if k in attrs)

        if not primary_keys:
            primary_keys = [key.name for key in class_mapper(table).primary_key]

        match = dict((key,values[key]) for key in primary_keys)

        instance = table.query.filter_by(**match).first()

        if instance:
            for k,v in values.iteritems():
                setattr(instance,k,v)
            prefix = 'Updating'
        else:
            instance = table(**values)
            self.model.add(instance)
            prefix = 'Adding'

        self.log.info('%s %s' % (prefix,match))

        try:
            self.model.commit()
        except:
            self.model.rollback()
            self.log.exception('Failed to commit')
            return False

        return True

if __name__ == '__main__':

    filename = sys.argv[1]

    store = Store(exitOnError=True)

    store.process(filename)

