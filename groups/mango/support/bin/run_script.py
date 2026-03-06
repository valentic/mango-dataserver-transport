#!/usr/bin/env python2

##########################################################################
#
#   Periodically run a script
#
#   Process client that runs an external script at defined intervals.
#
#   2023-05-06  Todd Valentic
#               Initial implementation
#
##########################################################################

from Transport import ProcessClient

import commands
import datetime
import sys

class RunScript(ProcessClient):

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        try:    
            self.init()
        except:
            self.log.exception('Init problem')
            self.abort()

    def init(self):

        self.rate = self.getRate('rate','1:00:00')
        self.script = self.get('script')
        self.exitOnError = self.getboolean('exitOnError',False)

        if not self.script:
            self.abort('No script listed')

        self.log.info('Script: %s' % self.script)
        self.log.info('Rate: %s' % self.rate.period)

    def run(self):

        while self.wait(self.rate):
            self.process(self.script)

    def process(self, script):
        
        self.log.info('Running script')
        starttime = datetime.datetime.now()

        status, output = commands.getstatusoutput(script)

        if status != 0:
            self.log.error('Problem running script:')
            self.log.error('  script: %s' % script)
            self.log.error('  status: %s' % status)
            self.log.error('  output: %s' % output)

            if self.exitOnError:
                self.abort('Exiting on error')

        elapsed = datetime.datetime.now() - starttime
        self.log.info('  - finished (%s)' % elapsed)

if __name__ == '__main__':
    RunScript(sys.argv).run()
