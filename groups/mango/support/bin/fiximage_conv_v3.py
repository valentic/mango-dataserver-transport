#!/usr/bin/env python

##########################################################################
#
#   Update v1 and v2 records to v3 format:
#
#   v1: no label, instrument attributes
#   v2: no instrument attribute
#
#   Determine the missing fields as:
#
#   v1: from filename
#   v2: from label
#
#   2022-04-21  Todd Valentic
#               Initial implementation
#
##########################################################################

from PIL import Image, PngImagePlugin
import sys
import os
import h5py
import signal

running = True

def signal_handler(sig, frame):
    global running
    running = False

label_to_instrument = {
    'Red Line': 'redline',
    'Green Line': 'greenline'
}

instrument_to_label = { v: k for k, v in label_to_instrument.items() }

def FixImage(filename):

    stats = os.stat(filename)
    image = Image.open(filename)
    info = PngImagePlugin.PngInfo()

    # Extract label from filename: mango-<site>-<instrument>-<date>-<time> 
    instrument = os.path.basename(filename).split('-')[2]

    if image.text['mango:version']=='1':

        label = instrument_to_label[instrument]

    elif image.text['mango:version']=='2':

        label = image.text['mango:label']

        if label:
            instrument = label_to_instrument[label] 

    else: # Nothing to do
        return True

    print(filename)
   
    for k,v in image.text.items():
        info.add_text(k,v)

    info.add_text('mango:version', '3')
    info.add_text('mango:label', label)
    info.add_text('mango:instrument', instrument)

    image.save(filename,  pnginfo=info)
    os.utime(filename, (stats.st_atime, stats.st_mtime))

    return True

def FixHDF5(filename):

    stats = os.stat(filename)

    with h5py.File(filename,'r') as output:
        image = output['image']

        if image.attrs['version'] >= 3:
            return True

    with h5py.File(filename,'r+') as output:
        print(filename)
        image = output['image']

        # Extract label from filename: mango-<site>-<instrument>-<date>-<time> 
        instrument = os.path.basename(filename).split('-')[2]

        if image.attrs['version'] == 1: 

            label = instrument_to_label[instrument]

            image.attrs['version'] = 3
            image.attrs['label'] = label
            image.attrs['instrument'] = instrument

        elif image.attrs['version'] == 2: 

            label = image.attrs['label']

            if label:
                instrument = label_to_instrument[label] 

            image.attrs['version'] = 3
            image.attrs['instrument'] = instrument

    os.utime(filename, (stats.st_atime, stats.st_mtime))

    return True

if __name__ == '__main__':

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
 
    if len(sys.argv)<2:
        print('Need to specifiy a root pathname')
        sys.exit(1)

    rootpath = sys.argv[1]

    for root, dirs, files in os.walk(rootpath):
        print(root)
        dirs.sort()
        for name in sorted(files):
            filename = os.path.join(root,name)

            if name.endswith('png'):
                FixImage(filename)

            if name.endswith('hdf5'):
                FixHDF5(filename)

            if not running:
                print('Interrupted, exiting early')
                sys.exit(8) 
    
    print('Finished')
    sys.exit(0)

