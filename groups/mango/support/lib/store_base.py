#!/usr/bin/env python

#####################################################################
#
#   Store data into database
#
#   2020-10-14  Todd Valentic
#               Initial implementation
#
#   2026-02-23  Todd Valentic
#               Update for Python 3 / DataTransport 3
#
#   2026-04-39  Todd Valentic
#               Only show adding/updating message in debug log
#
#####################################################################

import sys

from sqlalchemy.orm import class_mapper


class StoreBase:
    def __init__(self, model, data_handler, log=None, exit_on_error=True):

        if not log:
            self.setup_basic_logger()
        else:
            self.log = log

        self.model = model
        self.data_handler = data_handler
        self.exit_on_error = exit_on_error

    def setup_basic_logger(self):

        import logging

        self.log = logging
        logging.basicConfig(level=logging.INFO)

    def report_error(self, msg):
        self.log.error("Filename: %s", self.filename)
        if self.exit_on_error:
            self.log.exception(msg)
            raise RuntimeError(msg)
        else:
            self.log.error(msg)

    def process(self, filename, opts=None, *pos, **kw):

        self.filename = filename

        try:
            snapshots = self.data_handler.read(filename, opts=opts)
        except Exception: # noqa: BLE001
            self.report_error("Problem loading data")
            return False

        for snapshot in snapshots:
            self.update_record(snapshot, *pos, **kw)

        return True

    def update_record(self, snapshot, *pos, **kw):
        # Filled in by child class
        pass

    def lookup(self, match, table):
        return table.query.filter_by(**match).first()

    def lookupOrAdd(self, match, table):
        instance = table.query.filter_by(**match).first()

        if not instance:
            self.log.info("Added %s: %s", table, match)
            instance = table(**match)
            self.model.add(instance)

            try:
                self.model.commit()
            except:
                self.model.rollback()
                self.log.error("Problem adding")
                self.log.info("  - instance: %s", instance)
                self.log.info("  - match: %s", match)
                raise

        return instance

    def update(self, data, table, primary_keys=None):

        attrs = table.__dict__.keys()
        values = {k: v for k, v in data.items() if k in attrs}

        if not primary_keys:
            primary_keys = [key.name for key in class_mapper(table).primary_key]

        match = {key: values[key] for key in primary_keys}

        instance = table.query.filter_by(**match).first()

        if instance:
            for k, v in values.items():
                setattr(instance, k, v)
            prefix = "Updating"
        else:
            instance = table(**values)
            self.model.add(instance)
            prefix = "Adding"

        self.log.debug("%s %s", prefix, match)

        try:
            self.model.commit()
        except Exception:
            self.model.rollback()
            self.log.exception("Failed to commit")
            return False

        return True

