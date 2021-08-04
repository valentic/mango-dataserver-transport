#!/usr/bin/env python2

##########################################################################
#
#   Snapshot reader for Artemis binary data files.
#
#   The binary format is defined in the data transport camera monitor
#       on the remote systems. It is a compact format for transmitting
#       the images offsite and is our own creation. It has a set of
#       attribute followed by the sensor readout data.
#
#   Includes a binary reader and HDF5/PNG writers.
#
#   2021-07-28  Todd Valentic
#               Initial implementation
#
#   2021-07-30  Todd Valentic
#               Add write_png
#
##########################################################################

import bz2
import os
import sys
import struct
import h5py 
import numpy as np

from PIL import Image, PngImagePlugin

def as_str(v):
    # Strings from struct are fixed length and 0-padded
    # HDF5 doesn't like that, so trim off zeros
    return v.rstrip(b'\0')

UnitsCatalog = dict( 
    version             = '', 
    start_time          = 'Unix timetamp (UTC)',
    station             = '', 
    latitude            = 'degrees N', 
    longitude           = 'degrees E', 
    serialnum           = '', 
    device_name         = '', 
    label               = '', 
    exposure_time       = 'seconds',
    x                   = 'pixels', 
    y                   = 'pixels', 
    width               = 'pixels', 
    height              = 'pixels', 
    bytes_per_pixel     = 'bytes', 
    bin_x               = 'pixels', 
    bin_y               = 'pixels', 
    ccd_temp            = 'degrees C',
    set_point           = 'degrees C', 
    image_bytes         = 'bytes' 
)

 
class Snapshot:

    def __init__(self, rawdata, *pos, **kw):

        self.metadata = {}
        self.image = None

        version = struct.unpack_from('!B',rawdata)[0]
        parser = 'parse_version_%d' % version

        if hasattr(self, parser):
            getattr(self, parser)(rawdata)
        else:   
            raise ValueError('Unknown version: %d' % version)

    def parse_version_1(self, rawdata):

        header_fmt = '!Bi40sffi40sf7i2fi'
        values = struct.unpack_from(header_fmt, rawdata)

        self.metadata = dict( 
            version             = values[0],
            start_time          = values[1],
            station             = as_str(values[2]),
            latitude            = values[3],
            longitude           = values[4],
            serialnum           = values[5],
            device_name         = as_str(values[6]),
            label               = '', 
            exposure_time       = values[7],
            x                   = values[8],
            y                   = values[9],
            width               = values[10],
            height              = values[11],
            bytes_per_pixel     = values[12],
            bin_x               = values[13],
            bin_y               = values[14],
            ccd_temp            = values[15],
            set_point           = values[16],
            image_bytes         = values[17],
            )

        self.pixels = self.parse_pixels(rawdata, self.metadata, header_fmt)

    def parse_version_2(self, rawdata):

        header_fmt = '!Bi40s2fi40s40sf7i2fi'
        values = struct.unpack_from(header_fmt, rawdata)

        self.metadata = dict(
            version             = values[0],
            start_time          = values[1],
            station             = as_str(values[2]),
            latitude            = values[3],
            longitude           = values[4],
            serialnum           = values[5],
            device_name         = as_str(values[6]),
            label               = as_str(values[7]),
            exposure_time       = values[8],
            x                   = values[9],
            y                   = values[10],
            width               = values[11],
            height              = values[12],
            bytes_per_pixel     = values[13],
            bin_x               = values[14],
            bin_y               = values[15],
            ccd_temp            = values[16],
            set_point           = values[17],
            image_bytes         = values[18],
            )

        self.pixels = self.parse_pixels(rawdata, self.metadata, header_fmt)

    def parse_pixels(self, rawdata, metadata, header_fmt):

        width = metadata['width']
        height = metadata['height']

        image_size = width * height
        offset = struct.calcsize(header_fmt)
        pixels = struct.unpack_from('!%dH' % image_size, rawdata, offset)

        return np.array(pixels).astype(np.uint16).reshape((height,width))

    def write_hdf5(self, filename):

        with h5py.File(filename, 'w') as output:
            output.attrs['version'] = 1

            image = output.create_dataset('image', 
                                    data=self.pixels, 
                                    compression='gzip')

            image.attrs.update(self.metadata)

            units = output.create_group('units')
            units.attrs.update(UnitsCatalog)

    def write_png(self, filename):

        im = Image.fromarray(self.pixels)
        info = PngImagePlugin.PngInfo()

        for k,v in self.metadata.items():
            info.add_text('mango:'+k, str(v))

        im.save(filename, pnginfo=info)

def read(filename, *pos, **kw):

    # Camera files are one image per file.

    rawdata = open(filename).read()

    if filename.endswith('bz2'):
        rawdata = bz2.decompress(rawdata)

    return [Snapshot(rawdata, *pos, **kw)]

if __name__ == '__main__':

    if len(sys.argv)<2:
        filename = 'test_data/mango-cfs-camera_a-20210727-191500.dat.bz2'
    else:
        filename = sys.argv[1]
    
    snapshots = read(filename)

    for snapshot in snapshots:

        print('-'*70)
    
        for k,v in snapshot.metadata.items():
            print('%20s: %s %s' % (k, v, UnitsCatalog[k]))
        print('%20s: %s' % (snapshot.pixels.shape))
        print('-'*70)

        print('Saving snapshot as HDF5')

        snapshot.write_hdf5('tmp.hdf5')

        print('Saving snapshot as png')

        snapshot.write_png('tmp.png')
