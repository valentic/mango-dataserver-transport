#!/usr/bin/env python

from PIL import Image, PngImagePlugin
import sys
import os
import h5py
import signal

running = True

def signal_handler(sig, frame):
    global running
    running = False

correct_exposure_time = {
    'redline':      '230',
    'greenline':    '110'
}

def FixImage(filename):

    stats = os.stat(filename)
    image = Image.open(filename)
    info = PngImagePlugin.PngInfo()

    if image.text['mango:exposure_time']=='3':

        print filename

        for k,v in image.text.items():
            if k=='mango:exposure_time':
                instrument = image.text['mango:instrument']
                v = correct_exposure_time[instrument]

            info.add_text(k,v)

        image.save(filename,  pnginfo=info)
        os.utime(filename, (stats.st_atime, stats.st_mtime))

    return True

def FixHDF5(filename):

    stats = os.stat(filename)

    with h5py.File(filename,'r') as output:
        image = output['image']

        if image.attrs['exposure_time'] != 3:
            return True

    with h5py.File(filename,'r+') as output:
        print filename
        image = output['image']
        instrument = image.attrs['instrument']
        image.attrs['exposure_time'] = correct_exposure_time[instrument]

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
        for name in files:
            filename = os.path.join(root,name)
            #print filename

            if name.endswith('png'):
                FixImage(filename)

            if name.endswith('hdf5'):
                FixHDF5(filename)

            if not running:
                print('Interrupted, exiting early')
                sys.exit(8) 
    
    print('Finished')
    sys.exit(0)

