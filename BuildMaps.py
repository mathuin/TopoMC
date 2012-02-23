#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
import os
import sys
sys.path.append('..')
from newutils import cleanmkdir
from pymclevel import mclevel, box
import argparse

def center(name):
    worlddir = os.path.join('Worlds', name, 'level.dat')
    world = mclevel.fromFile(worlddir)
    bounds = world.bounds
    centerx = bounds.origin[0]+bounds.size[0]/2
    centerz = bounds.origin[2]+bounds.size[2]/2
    bounds = None
    world = None
    return centerx/16, centerz/16

def main(argv):
    parser = argparse.ArgumentParser(description='Builds c10t maps for regions.')
    parser.add_argument('--name', required=True, type=str, help='name of region to be mapped')
    parser.add_argument('--gmaps', action='store_true', help='generate Google Maps')
    args = parser.parse_args()

    print "Building %smaps for %s..." % ('Google ' if args.gmaps else '', args.name)

    (centerx, centerz) = center(args.name)

    if args.gmaps:
	cleanmkdir(os.path.join('Maps', args.name))
        command = 'C10T=../c10t/build/c10t ../c10t/scripts/google-api/google-api.sh -w Worlds/%s -o Maps/%s -O "-M 2048 -z --center %d,%d"' % (args.name, args.name, centerx, centerz)
    else:
        command = '../c10t/build/c10t -M 2048 -z -w Worlds/%s -o %s.png --center %d,%d' % (args.name, args.name, centerx, centerz)

    os.system(command)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

    
