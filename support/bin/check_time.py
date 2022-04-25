#!/usr/bin/env python

import os
import sys
import h5py
import datetime

if len(sys.argv)==1:
    basedir = '/data/transport/mango/archive'
else:   
    basedir=sys.argv[1]

def check(filename):

    #print(filename)

    with h5py.File(filename,'r') as f:
        ts = datetime.datetime.fromtimestamp(f['image'].attrs['start_time'])
        filetime = os.path.splitext(os.path.basename(filename))[0]
        filetime = ' '.join(filetime.split('-')[3:5])
        timestr = ts.strftime('%Y%m%d %H%M%S')

        if filetime != timestr:
            print(filename)
            print('File time: %s, data time: %s'  % (filetime, timestr))
            #sys.exit(0)

for root, dirs, files in os.walk(basedir):
    dirs.sort()
    #print(root)
    for filename in sorted(files):
        if filename.endswith('hdf5'):
            if 'greenline' in filename or 'redline' in filename:
                check(os.path.join(root, filename))

