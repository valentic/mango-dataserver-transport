#!/usr/bin/env python2

##########################################################################
#
#   Daily summary reports
#
#   2022-03-28  Todd Valentic
#               Initial implementation
#
##########################################################################

from Transport  import ProcessClient, NewsPostMixin

import sys
import schedule
import commands 
import fnmatch

class DailySummary (ProcessClient, NewsPostMixin):

    def __init__(self, argv):
        ProcessClient.__init__(self,argv)
        NewsPostMixin.__init__(self)

        self.scheduler = schedule.Scheduler()

        self.report_at = self.get('report.at','17:00:00')
        self.report_cmd = self.get('report.cmd')

        if not self.report_cmd:
            self.abort('No report command specified')

    def process(self):
  
        status, output = commands.getstatusoutput(self.report_cmd)

        if status != 0:
            self.log.error('Problem running report command:')
            self.log.error('  cmd=%s' % self.report_cmd)
            self.log.error('  status=%s' % status)
            self.log.error('  output=%s' % output)
            return
        
        reportDate = self.currentTime().strftime('%b %d, %Y')

        LEN=90

        msg = '\n'.join([
            "",
            "="*LEN,
            "MANGO Daily Summary Report for %s" % reportDate,
            "="*LEN,
            "",
            "-"*LEN,
            output.rstrip(),
            "-"*LEN,
            "",
            "Generated at %s" % self.currentTime().strftime('%b %d, %Y %H:%M:%S')
            ])

        self.newsPoster.setSubject('Report for %s' % reportDate)
        self.newsPoster.postText(msg)

        self.log.info(msg)

    def schedule_task(self, report_at, cmd):

        if fnmatch.fnmatch(report_at, ':??'):
            self.scheduler.every(1).minutes.at(report_at).do(cmd)
        elif fnmatch.fnmatch(report_at, '??:??'):
                self.scheduler.every(1).hours.at(report_at).do(cmd)
        elif fnmatch.fnmatch(report_at, '??:??:??'):
            self.scheduler.every(1).day.at(report_at).do(cmd)

    def run(self):

        self.schedule_task(self.report_at, self.process)
        
        while self.wait(1):
            try:
                self.scheduler.run_pending()
            except:
                self.log.exception('Error detected')

if __name__ == '__main__':
    DailySummary(sys.argv).run()

