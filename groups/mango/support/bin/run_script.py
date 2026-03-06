#!/usr/bin/env python

##########################################################################
#
#   Periodically run a script
#
#   Process client that runs an external script at defined intervals.
#
#   2023-05-06  Todd Valentic
#               Initial implementation
#
#   2026-02-26  Todd Valentic
#               Update for Python 3 / DataTransport 3
#
##########################################################################

import subprocess
import sys

from datatransport import ProcessClient


class RunScript(ProcessClient):
    def init(self):

        self.rate = self.config.get_rate("rate", "1:00:00")
        self.script = self.config.get("script")
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)

        if not self.script:
            self.abort("No script listed")

        self.log.info("Script: %s", self.script)
        self.log.info("Rate: %s", self.rate.period)

    def main(self):

        while self.wait(self.rate):
            self.process(self.script)

    def process(self, script):

        self.log.info("Running script")
        starttime = self.now()

        status, output = subprocess.getstatusoutput(script)

        if status != 0:
            self.log.error("Problem running script:")
            self.log.error("  script: %s", script)
            self.log.error("  status: %s", status)
            self.log.error("  output: %s", output)

            if self.exit_on_error:
                self.abort("Exiting on error")

        elapsed = self.now() - starttime
        self.log.info("  - finished (%s)", elapsed)


if __name__ == "__main__":
    RunScript(sys.argv).run()
