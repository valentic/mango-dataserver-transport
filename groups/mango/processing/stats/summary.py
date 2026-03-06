#!/usr/bin/env python

##########################################################################
#
#   Daily summary reports
#
#   2022-03-28  Todd Valentic
#               Initial implementation
#
#   2022-07-09  Todd Valentic
#               Add atStart option
#
#   2026-02-26  Todd Valentic
#               Update for Python 3 / DataTransport 3
#
##########################################################################

import fnmatch
import subprocess
import sys

import schedule
from datatransport import NewsPoster, ProcessClient


class DailySummary(ProcessClient):
    def init(self):

        self.news_poster = NewsPoster(self)
        self.scheduler = schedule.Scheduler()

        self.report_at = self.config.get("report.at", "17:00:00")
        self.report_cmd = self.config.get("report.cmd")
        self.report_at_start = self.config.get_boolean("report.at_start", False)

        if not self.report_cmd:
            self.abort("No report command specified")

    def process(self):

        status, output = subprocess.getstatusoutput(self.report_cmd)

        if status != 0:
            self.log.error("Problem running report command:")
            self.log.error("  cmd=%s", self.report_cmd)
            self.log.error("  status=%s", status)
            self.log.error("  output=%s", output)
            return

        report_date = self.now().strftime("%b %d, %Y")

        page_width = 90

        hrule_bold = "=" * page_width
        hrule = "-" * page_width
        title = f" MANGO Daily Summary Report for {report_date} "

        msg = f"""

{hrule_bold}
{title}
{hrule_bold}

{hrule}
{output.rstrip()}
{hrule}

Generated at {self.now().strftime("%b %d, %Y %H:%M:%S %Z")}
        """

        self.news_poster.set_subject(f"Report for {report_date}")
        self.news_poster.post_text(msg)

        self.log.info(msg)

    def schedule_task(self, report_at, cmd):

        if fnmatch.fnmatch(report_at, ":??"):
            self.scheduler.every(1).minutes.at(report_at).do(cmd)
        elif fnmatch.fnmatch(report_at, "??:??"):
            self.scheduler.every(1).hours.at(report_at).do(cmd)
        elif fnmatch.fnmatch(report_at, "??:??:??"):
            self.scheduler.every(1).day.at(report_at).do(cmd)

    def main(self):

        self.log.info("Running")

        self.schedule_task(self.report_at, self.process)

        if self.report_at_start:
            self.process()

        while self.wait(1):
            try:
                self.scheduler.run_pending()
            except Exception:
                self.log.exception("Error detected")

        self.log.info("Stopping")


if __name__ == "__main__":
    DailySummary(sys.argv).run()
