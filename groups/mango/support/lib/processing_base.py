#!/usr/bin/env python

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
#   2025-12-05  Todd Valentic
#               Handle case where we have no images in list (this can
#                   happen if there is only one image in an image island)
#
#   2026-02-23  Todd Valentic
#               Update to Python 3 / DataTransport 3
#
##########################################################################

import datetime
import multiprocessing
import os
import tempfile

import subprocess
from datatransport import ProcessClient
from datatransport.utilities import PatternTemplate

import model


def processing_handler(cmd):
    status, output = subprocess.getstatusoutput(cmd)
    return (status, output)


class ProcessingBase(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def init(self):

        self.task_cmd = self.config.get("task.cmd")
        self.formats = self.config.get_list("formats", "mp4")
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)

        self.replace_station = PatternTemplate("station")
        self.replace_instrument = PatternTemplate("instrument")
        self.replace_product = PatternTemplate("product")
        self.replace_filelist = PatternTemplate("filelist")
        self.replace_ext = PatternTemplate("ext")

        self.pool = multiprocessing.Pool(None)

        self.product = self.get_product(self.config.get("product"))

    def log_elapsed(self, msg, start_time, indent=0):

        # Strip off microseconds

        seconds = (self.now() - start_time).total_seconds()
        elapsed = datetime.timedelta(seconds=round(seconds))

        self.log.info("%s%s (%s)", " " * indent, msg, elapsed)

    def get_product(self, name):
        return model.ProcessedProduct.query.filter_by(name=name).first()

    def get_filelist(self, camera, date):

        station = camera.station.name
        instrument = camera.instrument.name

        engine = model.Base.metadata.bind
        sql = f"select * from image_list('{station}','{instrument}','{date}');"

        return [row[0] for row in engine.execute(sql).all()]

    def get_first_image(self, camera):

        query = model.Image.query.filter_by(stationinstrument_id=camera.id)
        query = query.order_by(model.Image.timestamp)

        return query.first()

    def find_next_image(self, camera, timestamp):

        Image = model.Image
        nextday = timestamp.date() + datetime.timedelta(days=1)
        query = Image.query.filter(
            Image.stationinstrument_id == camera.id, Image.timestamp >= nextday
        )
        query = query.order_by(Image.timestamp)

        return query.first()

    def update_db(self, camera, timestamp):

        match = {
            "timestamp": timestamp.date(),
            "stationinstrument_id": camera.id,
            "product_id": self.product.id,
        }

        instance = model.ProcessedData.query.filter_by(**match).first()

        if not instance:
            instance = model.ProcessedData(**match)
            model.add(instance)

            try:
                model.commit()
            except Exception:
                self.log.exception("Problem updating database")
                model.rollback()
                raise

    def make_products(self, camera, timestamp, formats):

        filelist = self.get_filelist(camera, timestamp)

        if not filelist:
            return 0

        with tempfile.NamedTemporaryFile(dir=".", delete=False, mode="w+t") as f:
            f.write("\n".join(filelist))

        cmd = self.replace_filelist(self.task_cmd, f.name)
        cmd = self.replace_station(cmd, camera.station.name)
        cmd = self.replace_instrument(cmd, camera.instrument.name)
        cmd = self.replace_product(cmd, self.product.name)
        cmd = timestamp.strftime(cmd)

        start_time = self.now()

        results = []

        try:
            tasks = [self.replace_ext(cmd, ext) for ext in formats]
            r = self.pool.map_async(processing_handler, tasks, callback=results.append)
            r.wait()
        finally:
            os.remove(f.name)

        self.log_elapsed(", ".join(formats), start_time, indent=6)

        if sum(entry[0] for entry in results[0]):
            self.log.info("results: %s", results)
            raise OSError("Problem running processing command: %s", results)

        self.update_db(camera, timestamp)

        return len(filelist)
