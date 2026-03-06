#!/usr/bin/env python

##########################################################################
#
#   Generate daily processing data products
#
#   2022-04-14  Todd Valentic
#               Initial implementation
#
#   2022-05-23  Todd Valentic
#               Handle situation where site has no images
#
#   2023-02-27  Todd Valentic
#               Refactor to be a generic data processing stage
#               Add restrict
#
#   2026-02-23  Todd Valentic
#               Update for Python 3 / DataTransport 3
#
##########################################################################

import configparser
import datetime
import fnmatch
import sys

import schedule

import model
from processing_base import ProcessingBase


class DateTracker:
    def __init__(self, filename, log):
        self.filename = filename
        self.log = log

        self.load()

    def load(self):
        self.tracker = configparser.ConfigParser()
        self.tracker.read(self.filename)

    def save(self):
        with open(self.filename, "w") as f:
            self.tracker.write(f)

    def get_section(self, camera):

        station = camera.station.name
        instrument = camera.instrument.name

        return f"{station}.{instrument}"

    def get(self, camera):

        section = self.get_section(camera)

        if self.tracker.has_section(section):
            timestr = self.tracker.get(section, "timestamp")
            timestamp = datetime.datetime.strptime(timestr, "%Y-%m-%d").replace(
                tzinfo=datetime.UTC
            )
            count = self.tracker.getint(section, "count")
        else:
            timestamp = None
            count = 0

        return timestamp, count

    def put(self, camera, timestamp, count):

        section = self.get_section(camera)

        if not self.tracker.has_section(section):
            self.tracker.add_section(section)

        self.tracker.set(section, "timestamp", str(timestamp.date()))
        self.tracker.set(section, "count", str(count))

        self.save()


class ProcessingDaily(ProcessingBase):
    def __init__(self, argv):
        ProcessingBase.__init__(self, argv)

    def init(self):
        ProcessingBase.init(self)

        self.scheduler = schedule.Scheduler()
        self.tracker = DateTracker("tracker.ini", self.log)
        self.schedule_at = self.config.get("schedule.at", "17:00:00")
        self.run_at_start = self.config.get_boolean("run_at_start", False)
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)
        self.max_retries = self.config.get_int("max_retries", 5)
        self.restrict = self.config.get_list("restrict")

    def process_camera(self, camera):

        lasttime, lastcount = self.tracker.get(camera)
        timestamp = None

        if not lasttime:
            image = self.get_first_image(camera)
            if image:
                timestamp = image.timestamp
                self.log.debug("No history, start with %s", timestamp.date())
        else:
            lastlist = self.get_filelist(camera, lasttime)

            if len(lastlist) != lastcount:
                self.log.debug(
                    "Need to reprocess %s. Image count differs (%d vs %d)",
                    lasttime,
                    lastcount,
                    len(lastlist),
                )
                timestamp = lasttime
            else:
                image = self.find_next_image(camera, lasttime)
                if image:
                    self.log.debug("Next time is %s", image.timestamp.date())
                    timestamp = image.timestamp

        if not timestamp:
            # No more images to process
            return False

        self.log.info(
            "  - %s %s %s",
            camera.station.name,
            camera.instrument.name,
            timestamp.date(),
        )

        num_images = self.make_products(camera, timestamp, self.formats)

        self.tracker.put(camera, timestamp, num_images)

        return True

    def process(self):

        for attempt in range(self.max_retries):
            try:
                self._process()
            except Exception:
                model.session.rollback()
                self.log.exception("Problem detected while processing")
            else:
                return

            if not self.running:
                break

            self.log.info("Retry %s of %s", attempt + 1, self.max_retries)

        if self.exit_on_error:
            self.abort("Exiting on error")

        raise RuntimeError("Failed to process. Out of retries")

    def _process(self):

        self.log.info("Processing start")
        starttime = self.now()

        for camera in model.StationInstrument.query.all():
            si = f"{camera.station.name}-{camera.instrument.name}"

            if self.restrict and si not in self.restrict:
                continue

            while self.process_camera(camera) and self.running:
                pass

            if not self.running:
                break

        self.log_elapsed("Processing finished", starttime)

    def schedule_task(self, at, cmd):

        self.log.info("Run task at %s", at)

        if fnmatch.fnmatch(at, ":??"):
            self.scheduler.every(1).minutes.at(at).do(cmd)
        elif fnmatch.fnmatch(at, "??:??"):
            self.scheduler.every(1).hours.at(at).do(cmd)
        elif fnmatch.fnmatch(at, "??:??:??"):
            self.scheduler.every(1).day.at(at).do(cmd)

    def main(self):

        self.log.info("Running")

        if self.run_at_start:
            self.process()

        self.schedule_task(self.schedule_at, self.process)

        while self.wait(1):
            self.scheduler.run_pending()

        self.log.info("Exiting")


if __name__ == "__main__":
    ProcessingDaily(sys.argv).run()
