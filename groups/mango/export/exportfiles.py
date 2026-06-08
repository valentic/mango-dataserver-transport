#!/usr/bin/env python

##########################################################################
#
#   Specialized verison of postfiles that will populate the filesystem
#   directories based on the current tincan stations.
#
#   2021-07-16  Todd Valentic
#               Initial implementation
#
#   2026-06-08  Todd Valentic
#               Update for Python3 / Transport3
#
##########################################################################

from postfiles import PostFiles

import os
import subprocess


class ExportFiles(PostFiles):

    def init(self):
        super().init()

        self.export_path = self.config.get_path("path.project.export", ".")
        self.sql_base = self.config.get("sql.base")

    def preprocess(self):

        stations = self.list_stations()

        for station in stations:
            try:
                self.create_files(station)
            except Exception:
                self.log.exception("Failed to make dirs for %s" % station)

    def list_stations(self):

        sql = "select name from mesh_node where active=true"
        sql_cmd = f'{self.sql_base} -t -c "{sql}"'

        status, output = subprocess.getstatusoutput(sql_cmd)

        if status == 0:
            return output.split()
        else:
            self.log.error("Failed to get station list")
            self.log.error("cmd=%s" % sql_cmd)
            self.log.error("output=%s" % output)
            return []

    def create_files(self, station):

        basepath = self.export_path / station

        for name in self.filegroups:
            pathname = basepath / name

            if not pathname.exists():
                try:
                    original_umask = os.umask(0o002)
                    #pathname.mkdir(mode=0o775, parents=True, exist_ok=True)
                    pathname.mkdir(parents=True, exist_ok=True)
                    self.log.info("Creating %s" % pathname)
                except Exception:
                    self.log.exception("Failed to create %s" % pathname)
                finally:
                    os.umask(original_umask)


if __name__ == "__main__":
    ExportFiles().run()
