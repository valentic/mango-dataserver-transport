#!/usr/bin/env python2

##########################################################################
#
#   Save image snapshots in multiple formats. This function is a plugin 
#   to the ArchiveGroups pipeline. To enable it, set it as the callback:
#
#       callback.module:        image_save
#       callback.function:      write
#
#   The supported output types are:
#
#       raw  - the oringinating compact binary format 
#       hdf5 - HDF5 with metadata attributes
#       png  - 16-bit monochrome image with metadata
#
#   To enable the outputs:
#
#       output.raw      (default False)
#       output.hdf5     (default True)
#       output.png      (default True)
#
#   2021-07-29  Todd Valentic
#               Initial implementation
#
#   2021-07-30  Todd Valentic
#               Add png output
#
##########################################################################

import artemis_data

def write(self, filename):

    save_hdf5 = self.getboolean('output.hdf5', True)
    save_raw = self.getboolean('output.raw', False)
    save_png = self.getboolean('output.png', True)

    basename = filename.replace('.dat.bz2','')
    filenames = []

    # The raw file has only one snapshot 
    
    snapshot = artemis_data.read(filename)[0]

    if save_hdf5:
        outname = basename+'.hdf5'
        snapshot.write_hdf5(outname)
        filenames.append(outname)

    if save_png:
        outname = basename+'.png'
        snapshot.write_png(outname)
        filenames.append(outname)
        
    if save_raw:
        filenames.append(filename)

    return filenames

