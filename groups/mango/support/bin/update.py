#!/usr/bin/env python

#########################################################
#
#   Update tables
#
#   2012-11-09  Todd Valentic
#               Initial implementation
#
#   2026-11-20  Todd Valentic
#               Update for python3
#               optparser -> argparse
#
#########################################################

import sys
import argparse
import mixinconfig
import logging

import model

logging.basicConfig(level=logging.INFO)

VERSION="2.0"

class Reload:
    def __init__(self, configfile):

        config = mixinconfig.MixinConfigParser()
        config.read(configfile)

        current = {}

        for section in config.sections():
            _class = getattr(model, config.get(section, "_class"))

            if _class in current:
                current[_class].append(section)
            else:
                current[_class] = [section]

            params = {}

            for key in config.options(section):
                if not key.startswith("_"):
                    params[key] = config.get(section, key)

            # filter to match columns in database

            attrs = _class.__dict__.keys()
            params = dict((k, v) for k, v in params.items() if k in attrs)

            match = {}
            for key in config.get_list(section, "_match"):
                match[key] = params[key]

            instance = _class.query.filter_by(**match).first()

            if instance:
                logging.info("Updating %s", section)
                for k, v in params.items():
                    setattr(instance, k, v)

            else:
                instance = _class(**params)
                model.add(instance)

                logging.info("Adding %s" % section)

        try:
            model.commit()
            logging.info("Commiting")
        except:
            model.rollback()
            logging.exception("Failed to commit")
            sys.exit(1)

    def expire(self, current):

        for _class, curnames in current.items():
            oldobjs = dict([(str(k.id), k) for k in _class.query.all()])
            expired = set(oldobjs).difference(curnames)
            for name in expired:
                obj = oldobjs[name]
                model.delete(obj)
                logging.info("Expired %s" % obj)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("filenames", metavar="filename", nargs="+")
    parser.add_argument("-V", "--version", action="version", version=VERSION)

    args = parser.parse_args()

    for filename in args.filenames:
        Reload(filename)

    sys.exit(0)
