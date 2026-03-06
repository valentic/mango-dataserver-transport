#!/usr/bin/env python3

##########################################################################
#
#   Symlink old movie files into transport data heirarchy.
#
#   Once done, make sure to run catalog_image to update database. An easy
#   way to generate the file list is to search for symlinks ending in mp4.
#
#   2022-07-26  Todd Valentic
#               Initial implementation
#
##########################################################################

import os
import sys
import argparse
import logging
import pathlib
import datetime

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

NAMEMAP = {
    'Pisgah, NC':                       'par',
    'Bridger, MT':                      'brg',
    'Hat Creek, CA':                    'hco',
    'Eastern Iowa Observatory, IA':     'eio',
    'Capitol Reef, UT':                 'cfs',
    'Madison, KS':                      'mdk',
    'French Camp, MS':                  'frc',
}

SITEMAP = {
    'Pisgah':       'par',
    'Bridger':      'brg',
    'HatCreek':     'hco',
    'Iowa':         'eio',
    'CRFS':         'cfs',
    'Madison':      'mdk',
    'Rainwater':    'frc',
}

instrument = 'redline'

class Linker:

    def __init__(self, args):
        self.args = args

    def makeOutputName(self, sitecode, instrument, timestamp, ext):

        root = pathlib.Path('/data/transport/mango/archive')
        year = timestamp.strftime('%Y')
        jday = timestamp.strftime('%j')
        tstr = timestamp.strftime('%Y%m%d')
        name = f'mango-{sitecode}-{instrument}-quicklook-{tstr}{ext}'

        path = root / sitecode / instrument / 'quicklook' / year / jday / name

        return path

    def run(self):

        for root, dirs, files in os.walk(self.args.rootpath):

            for filename in files:
                if not filename.endswith('mp4'):
                    continue

                print(f'{root} {filename}')

                basename, ext = os.path.splitext(filename)

                if basename.endswith('.mpeg'):
                    # Handle occasional case where filenames end with '.mpeg.mp4'
                    basename = os.path.splitext(basename)[0]

                sitename = basename[0:-7]
                datecode = basename[-7:]
                sitecode = SITEMAP[sitename]

                timestamp = datetime.datetime.strptime(datecode, '%b%d%y')

                inputname  = pathlib.Path(root) / filename
                outputname = self.makeOutputName(sitecode, self.args.instrument, timestamp, ext)

                print(f'    {sitecode} {datecode} {timestamp}')
                print(f'    {inputname} -> {outputname}')
                print(f'    {outputname.parent}')

                outputname.parent.mkdir(parents=True, exist_ok=True)
    
                if outputname.is_symlink():
                    outputname.unlink()

                outputname.symlink_to(inputname)

        return True

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('rootpath')

    parser.add_argument('-i','--instrument',default='redline')

    args = parser.parse_args()

    linker = Linker(args)

    sys.exit(EXIT_SUCCESS if linker.run() else EXIT_FAILURE)



