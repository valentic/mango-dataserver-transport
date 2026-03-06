#!/usr/bin/env python

##########################################################################
#
#   Plot MANGO uptime values from the CVS file produced by the script:
#
#       /opt/transport/groups/mango/support/lib/sql/uptime_csv.sql
#
#   2023-05-04  Todd Valentic
#               Initial implementation
#
#   2026-03-02  Todd Valentic
#               Use pathlib for output
#
##########################################################################

import argparse
import logging
import os
import pathlib
import sys

import matplotlib.pyplot as plt
import pandas
import seaborn

logger = logging.getLogger(__name__)


class Plotter:
    def __init__(self, args):
        self.args = args

        args.output.parent.mkdir(parents=True, exist_ok=True)

    def run(self):

        logger.debug("Loading data from %s", self.args.inputfile)

        df = pandas.read_csv(self.args.inputfile, parse_dates=["day"])
        num_cameras = len(df["camera"].unique())

        logger.debug("Generating plot")

        seaborn.set_theme(style="white", rc={"axes.facecolor": (0, 0, 0, 0)})

        pal = seaborn.cubehelix_palette(num_cameras, rot=-0.25, light=0.7)
        g = seaborn.FacetGrid(
            df,
            row="camera",
            hue="camera",
            aspect=25,
            height=0.5,
            palette=pal,
            xlim=(pandas.Timestamp("2012"), pandas.Timestamp("now")),
        )

        g.map(seaborn.histplot, "day", discrete=True)

        g.refline(y=0, linewidth=2, linestyle="-", color=None, clip_on=False)

        def label(x, color, label):
            ax = plt.gca()
            station, instrument = label.split()
            label = f"{station.upper()} {instrument.capitalize()}"
            ax.text(
                0,
                0.2,
                label,
                fontweight="bold",
                color=color,
                ha="left",
                va="center",
                transform=ax.transAxes,
            )

        g.map(label, "day")

        g.figure.subplots_adjust(hspace=0.25)
        g.set_titles("")
        g.set(yticks=[], ylabel="", xlabel="")
        g.despine(bottom=True, left=True)

        g.figure.suptitle("MANGO Site Uptime", fontsize=25, fontweight="bold")
        plt.savefig(self.args.output)

        logger.debug("Output saved to %s", self.args.output)

        return True


def main():

    desc = "MANGO Uptime Plotter"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        "-o",
        "--output",
        default="uptime.png",
        type=pathlib.Path,
        help="Output filename",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument("inputfile")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    result = Plotter(args).run()

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
