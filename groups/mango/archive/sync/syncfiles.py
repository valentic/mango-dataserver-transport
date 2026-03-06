#!/usr/bin/env python

##########################################################################
#
#   Sync remote data products:
#
#       - FPI/Mango winds
#
#   2023-02-08  Todd Valentic
#               Initial implementation
#
#   2023-02-10  Todd Valentic
#               Refactor database/output file naming
#
#   2023-02-14  Todd Valentic
#               Add transcoding for webm
#
#   2023-11-27  Todd Valentic
#               Handle unknown name parsing better.
#
#   2024-02-01  Todd Valentic
#               Upstream filenames have changed. Now using prefix MANGO_
#                   instead of DASI_. Adapt name parser to handle both.
#
#   2026-02-20  Todd Valentic
#               Update for Python3 / DataTransport3
#
##########################################################################

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import model
import pytz
from datatransport import ProcessClient
from datatransport.utilities import PatternTemplate, datefunc


class DataFile:
    # TBD - expand to be a factory for multiple data products

    def __init__(self, entry):

        self.entry = entry

        self.src_modtime, self.src_filesize, self.src_filename = entry.split()

        # src filenames are in the form <prefix>_<date>_<prod>.mp4
        # 2024-01-23: Looks like there was a name change. Now
        # they are prefixed with MANGO_. Add both to the pattern:
        # <prefix> - MANGO | DASI
        # <date>   - YYYYmmdd
        # <prod>   - green or red
        # Example: DASI_20230206_green.mp4

        pattern = ".*(MANGO|DASI)_([0-9]+)_([a-z]+).mp4"
        namemap = dict(green="winds-greenline", red="winds-redline")

        _prefix, datestr, namekey = re.match(pattern, self.src_filename).groups()

        self.timestamp = datefunc.strptime(datestr, "%Y%m%d", tzinfo=pytz.utc)
        self.product = self._lookup_product(namemap[namekey])

    def _lookup_product(self, name):
        match = dict(name=name)
        return model.FusionProduct.query.filter_by(**match).first()

    def _lookup_datafile(self, timestamp, product):
        match = dict(timestamp=timestamp, product_id=product.id)
        return model.FusionData.query.filter_by(**match).first()

    def is_valid(self):

        match = dict(
            timestamp=self.timestamp,
            product_id=self.product.id,
            src_filesize=self.src_filesize,
            src_filename=self.src_filename,
            src_modtime=self.src_modtime,
        )

        instance = model.FusionData.query.filter_by(**match).first()

        return instance is not None

    def update_db(self):

        match = dict(
            timestamp=self.timestamp,
            product_id=self.product.id,
        )

        instance = model.FusionData.query.filter_by(**match).first()

        if not instance:
            instance = model.FusionData(**match)
            model.add(instance)

        instance.src_filesize = self.src_filesize
        instance.src_filename = self.src_filename
        instance.src_modtime = self.src_modtime

        try:
            model.commit()
        except Exception:
            model.rollback()
            raise


class Fetcher(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def init(self):

        try:
            self.read_config()
        except Exception:
            self.log.exception("Problem reading config")
            self.abort()

        self.checksumFile = Path("checksum.dat")

        self.checksum = self.load_checksum()

    def read_config(self):

        self.scan_cmd = self.config.get("scan.cmd")
        self.fetch_cmd = self.config.get("fetch.cmd")
        self.output_name = self.config.get("output.name")

        self.rate = self.config.get_rate("rate", "5:00")
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)

        self.replace_filename = PatternTemplate("filename", ".")
        self.replaceProduct = PatternTemplate("product")

        self.log.info("Scan cmd: %s", self.scan_cmd)
        self.log.info("Fetch cmd: %s", self.fetch_cmd)

    def load_checksum(self):

        try:
            return self.checksumFile.read_text(encoding="utf-8")
        except Exception:
            return ""

    def save_checksum(self, checksum):

        self.checksumFile.write_text(checksum, encoding="utf-8")

        self.checksum = checksum

        self.log.info("Saving checksum")

    def download(self, datafile):

        self.log.info("  downloading")

        cmd = self.replace_filename(self.fetch_cmd, datafile.src_filename)

        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            self.log.error("Problem downloading:")
            self.log.error("  cmd: %s", cmd)
            self.log.error("  status: %s", status)
            self.log.error("  output: %s", output)

            raise OSError(f"Failed to download {datafile.src_filename}")

    def copy_to_archive(self, datafile):

        destname = datafile.timestamp.strftime(self.output_name)
        destname = self.replace_filename(
            destname, os.path.basename(datafile.src_filename)
        )
        destname = self.replaceProduct(destname, datafile.product.name)

        self.log.info("  copy to archive: %s", destname)

        srcname = os.path.basename(datafile.src_filename)

        dirname = os.path.dirname(destname)

        if not os.path.exists(dirname):
            os.makedirs(dirname)

        shutil.copyfile(srcname, destname)

        self.transcode(destname)

        os.remove(srcname)

    def transcode(self, filename):

        if not filename.endswith("mp4"):
            return

        self.log.info("  transcode")

        destname = filename.replace(".mp4", ".webm")

        cmd = f"ffmpeg -y -hide_banner -loglevel error -i {filename} -c:v libvpx-vp9 -crf 30 -b:v 0 -b:a 128k -c:a libopus {destname}"

        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            self.log.error("Error transcoding")
            self.log.error("cmd: %s", cmd)
            self.log.error("status: %s", status)
            self.log.error("output: %s", output)
            if self.exit_on_error:
                raise OSError("Error transcribing")

    def process(self):

        status, output = subprocess.getstatusoutput(self.scan_cmd)
        self.log.debug("status: %s", status)
        self.log.debug("output: %s", output)

        new_checksum = hashlib.md5(output.encode("utf-8")).hexdigest()

        if new_checksum == self.checksum:
            self.log.debug("No change detected")
            return

        # DEBUG - REMOVE ONCE FIXED
        try:
            output = output.split("\n")
        except Exception:
            self.log.error("*** Problem splitting")
            self.log.error("output=%s", output)
            raise

        self.log.info("Checking %d files", len(output))
        self.log.debug("output=%s", output)

        for entry in output:
            try:
                datafile = DataFile(entry)
            except (AttributeError, ValueError) as err:
                self.log.error("Failed to process entry: %s", entry)
                self.log.error(err)
                continue

            if not datafile.is_valid():
                self.log.info(datafile.src_filename)
                self.download(datafile)
                self.copy_to_archive(datafile)
                datafile.update_db()

            if not self.running:
                return

        self.save_checksum(new_checksum)

    def main(self):
        self.log.info("Start")

        while self.wait(self.rate):
            try:
                self.process()
            except Exception:
                # Sometimes we pick up errors in the remote database
                model.rollback()

                self.log.exception("Problem processing")
                if self.exit_on_error:
                    break

        self.log.info("Stop")


if __name__ == "__main__":
    Fetcher(sys.argv).run()
