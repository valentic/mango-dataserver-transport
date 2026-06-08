#!/usr/bin/env python

############################################################################
#
#   Post new files
#
#   2019-06-27  Todd Valentic
#               Initial implementation. Based on PostDataFiles.py
#
#   2019-07-23  Todd Valentic
#               Filter out names starting with '.' (these are partial files)
#
#   2019-08-03  Todd Valentic
#               Add time parsing for vmti names
#
#   2021-07-16  Todd Valentic
#               Make filename time parsing optional
#
#   2021-07-17  Todd Valentic
#               Add serial_num option
#               Use path, filename, pathname nomenclature
#
#   2026-06-08  Todd Valentic
#               Update for Python3 / datatransport3
#
############################################################################

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import ConfigComponent
from datatransport.utilities import PatternTemplate, size_desc 
from dateutil import parser

import re
import os
from pathlib import Path
import bz2
import sys
import time
import subprocess
import datetime
import uuid


class FileGroup(ConfigComponent):

    def __init__(self, *args, **kwargs):
        ConfigComponent.__init__(self, "filegroup", *args, **kwargs)

        self.start_path = self.config.get_path("start.path", ".")
        self.match_paths = self.config.get_list("match.paths", "*")
        self.match_names = self.config.get_list("match.names", "*")
        self.compress = self.config.get_boolean("compress", False)
        self.remove_files = self.config.get_boolean("remove_files", False)
        self.include_last = self.config.get_boolean("include_last", True)
        self.start_current = self.config.get_boolean("start_current", False)
        self.max_files = self.config.get_int("max_files")
        self.enable_parse_time = self.config.get_boolean("parse_time", True)
        self.enable_serial_num = self.config.get_boolean("serial_num", False)

        self.pathRule = PatternTemplate("path", "/")

        self.newsgroupTemplate = self.config.get("post.newsgroup.template")

        self.posters = {}
        self.time_filename = Path(f"{self.name}.timestamp")

        if not self.time_filename.exists():
            # Default to sometime long ago
            self.time_filename.write_text("0", encoding="utf-8")
            t = time.mktime((1975, 1, 1, 0, 0, 0, 0, 0, 0))
            os.utime(self.time_filename, (t, t))

        if self.start_current:
            os.utime(self.time_filename, None)

        self.log.info("Watching for files in %s" % self.start_path)
        self.log.info("   - match paths %s" % " ".join(self.match_paths))
        self.log.info("   - match names %s" % " ".join(self.match_names))

    def parse_time(self, filename):

        # Standard format - 20190802-200555C00SEQ01.ntf
        # Log format - hs-07-20190803-165804.log
        # VMTI format - vmti_08-02-2019_UTC20-04-55_0000_00.4607

        regexs = [
            (r"\d{8}.\d{6}", r"%Y%m%d-%H%M%S"),
            (r"\d{2}-\d{2}-\d{4}_UTC\d{2}-\d{2}-\d{2}", r"%m-%d-%Y-UTC%H-%M-%S"),
        ]

        timestamp = None

        for regex, timefmt in regexs:
            try:
                timestr = re.findall(regex, filename)[0]
                timestr = timestr.replace("_", "-")
                timestamp = datetime.datetime.strptime(timestr, timefmt)
                timestamp = timestamp.replace(tzinfo=datetime.UTC)
                break
            except:
                pass

        if timestamp is None:
            self.log.warn("Unable to parse timestamp from filename: %s" % filename)

        return timestamp

    def post(self, pathname):

        if self.enable_parse_time:
            timestamp = self.parse_time(pathname.name)
        else:
            timestamp = None

        newsgroup = self.pathRule(self.newsgroupTemplate, str(pathname))
        filesize = pathname.stat().st_size 

        self.log.info(
            "  - posting %s (%s) to %s" % (pathname, size_desc(filesize), newsgroup)
        )

        if not newsgroup in self.posters:
            self.config.set("post.newsgroup", newsgroup)
            poster = NewsPoster(self, prefix="post")
            self.posters[newsgroup] = poster

        headers = {}

        if self.enable_serial_num:
            headers["X-datatransport-SerialNum"] = str(uuid.uuid4())

        self.posters[newsgroup].post([pathname], date=timestamp, headers=headers)

    def process_file(self, pathname):

        self.log.info("Processing %s" % pathname)

        bzipext = ".bz2"
        basename = pathname.name 
        baseext = pathname.suffix 
        isCompressed = baseext == bzipext
        zipname = Path(basename + bzipext)

        if self.compress and not isCompressed:
            self.log.debug("  - compressing file")

            with pathname.open("rb") as infile:
                with bz2.BZ2File(zipname, "wb", compresslevel=9) as outfile:
                    shutil.copyfileobj(infile, outfile)

            orgsize = pathname.stat().st_size
            zipsize = zipname.stat().st_size

            if orgsize > 0:
                zippct = (zipsize / orgsize) * 100
            else:
                zippct = 0

            self.log.info(
                "  - %s -> %s (%d%%)" % (size_desc(orgsize), size_desc(zipsize), zippct)
            )

            postfile = zipname

        else:
            postfile = pathname

        self.post(postfile)

        # Cleanup files

        zipname.unlink(missing_ok=True)

        if self.remove_files:
            pathname.unlink()

    def join_list(self, name, parts):

        result = ['-%s "%s"' % (name, part) for part in parts]
        result = " -o ".join(result)
        result = rf"\( {result} \)"

        return result

    def find_files(self):

        names = self.join_list("name", self.match_names)
        paths = self.join_list("path", self.match_paths)

        cmd = "find %s -newer %s -type f %s %s -print" % (
            self.start_path,
            self.time_filename,
            paths,
            names,
        )

        status, output = subprocess.getstatusoutput(cmd)

        self.log.debug("cmd=%s" % cmd)

        if status != 0:
            return []

        filelist = []

        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("."):
                continue
            filelist.append(Path(line))

        filelist.sort()

        if not self.include_last:
            filelist = filelist[0:-1]  

        if self.max_files:  
            if self.remove_files:
                for filename in filelist[:-max_files]:
                    filename.unlink()
                    
            filelist = filelist[-self.max_files:]

        return filelist

    def process(self):

        filenames = self.find_files()
        self.log.debug("Polling - found %d new files." % len(filenames))

        for filename in filenames:
            if not self.is_running():
                break

            timestamp = filename.stat().st_mtime 
            self.process_file(filename)
            os.utime(self.time_filename, (timestamp, timestamp))


class PostFiles(ProcessClient):

    def init(self):

        self.pollrate = self.config.get_rate("pollrate", "5:00")
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)
        self.filegroups = self.config.get_components("filegroups", factory=FileGroup)

    def preprocess(self):
        return

    def postprocess(self):
        return

    def process(self):

        self.preprocess()

        for name, filegroup in self.filegroups.items():
            try:
                filegroup.process()
            except SystemExit:
                self.stop()
            except Exception:
                self.log.exception("Problem processing filegroup %s" % name)
                if self.exit_on_error:
                    self.stop()

            if not self.is_running():
                break

        self.postprocess()

    def main(self):

        while self.wait(self.pollrate):
            try:
                self.process()
            except SystemExit:
                break
            except:
                self.log.exception("Problem detected")
                if self.exit_on_error:
                    break

        self.log.info("Exiting")


if __name__ == "__main__":
    PostFiles().run()
