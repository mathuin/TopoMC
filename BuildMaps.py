#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
import os
import sys
sys.path.append('..')
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
    return centerx, centerz

def main(argv):
    parser = argparse.ArgumentParser(description='Builds c10t maps for regions.')
    parser.add_argument('--name', required=True, type=str, help='name of region to be mapped')
    parser.add_argument('--gmaps', action='store_true', help='generate Google Maps')
    args = parser.parse_args()

    print "Building %smaps for %s..." % ('Google ' if args.gmaps else '', args.name)

    (centerx, centerz) = center(args.name)

    if args.gmaps:
        command = 'rm -rf Maps/%s && cd ../c10t/build && ../scripts/google-api/google.api.sh -w ../../TopoMC/Worlds/%s -o ../../TopoMC/Maps/%s -O "-z --center %d,%d' % (args.name, args.name, args.name, centerx, centerz)
    else:
        command = '../c10t/build/c10t -z -w Worlds/%s -o %s.png' % (args.name, args.name)

    os.system(command)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

    
