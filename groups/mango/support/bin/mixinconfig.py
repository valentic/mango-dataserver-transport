#!/usr/bin/env python

##########################################################################
#
#   Mixin enhanced ConfigParser
#
#   2012-04-26  Todd Valentic
#               Initial implementation
#
#   2014-02-14  Todd Valentic
#               Return non-mixin options in DEFAULTS in options()
#
#   2021-08-07  Todd Valentic
#               Add include feature
#
#   2021-11-15  Todd Valentic
#               Filter options pattern _* from defaults on include
#
#   2026-11-20  Todd Valentic
#               Update to python3
#
##########################################################################

from configparser import ConfigParser


class MixinConfigParser(ConfigParser):
    def options(self, section):

        opts = list(self._sections[section].keys())

        if "mixin" in opts:
            opts.remove("mixin")

        mixins = self.mixins(section)

        for option in self._defaults:
            for mixin in mixins:
                if option.startswith(mixin):
                    key = option.replace(mixin + ".", "")
                    if key not in opts:
                        opts.append(key)
                    continue
            opts.append(option)

        return opts

    def mixins(self, section):
        if self.has_option(section, "mixin"):
            return ConfigParser.get(self, section, "mixin").split()
        else:
            return []

    def read(self, filenames):

        if not isinstance(filenames, list):
            filenames = [filenames]

        for filename in filenames:
            super().read(filename)

            sections = ["DEFAULT"] + self.sections()

            for section in sections:
                for filename in self.get_list(section, "include"):
                    self.include_file(section, filename)

                self.remove_option(section, "include")

    def include_file(self, dest, filename):

        config = MixinConfigParser()
        config.read(filename + ".conf")

        defaults = []

        for option, value in config.items("DEFAULT", raw=True):
            if not option.startswith("_"):
                self.set("DEFAULT", option, value)
            defaults.append(option)

        for section in config.sections():
            for option, value in config.items(section, raw=True):
                if option in defaults:
                    continue
                key = ".".join([filename, section, option])
                self.set(dest, key, value)

    def get(self, section, option, default=None, **kw):

        lookupStack = [option]

        for mixin in self.mixins(section):
            lookupStack.append("%s.%s" % (mixin, option))

        for option in lookupStack:
            if self.has_option(section, option):
                return super().get(section, option, **kw)

        return default

    def getint(self, section, option, default=None, **kw):
        try:
            return super().getint(section, option, **kw)
        except:
            return default

    def getfloat(self, section, option, default=None, **kw):
        try:
            return super().getfloat(section, option, **kw)
        except:
            return default

    def getboolean(self, section, option, default=None, **kw):
        try:
            return super().getboolean(section, option, **kw)
        except:
            return default

    def get_list(self, *pos, **kw):
        if "default" not in kw:
            kw["default"] = ""

        return self.get(*pos, **kw).split()


if __name__ == "__main__":
    config = MixinConfigParser()
    config.read("station.conf")

    print("Looking up mangonetwork")
    print("[mangnetwork] id = %s" % config.get("mangonetwork", "id"))

    print(f"Options for mangonetwork = {config.options('mangonetwork')}")

    for opt in config.options("mangonetwork"):
        print(f"{opt} = {config.get('mangonetwork', opt)}")
