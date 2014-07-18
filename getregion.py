#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
from region import Region
import sys
import argparse


def main():
    """Creates a specified region and downloads files from USGS."""
    # example:
    # ./GetRegion.py --name BlockIsland --ymax 41.2378 --ymin 41.1415 --xmin -71.6202 --xmax -71.5332

    # parse options and get results
    parser = argparse.ArgumentParser(description='Create regions and download files from USGS.')
    parser.add_argument('--name', required=True, type=str, help='name of the region to be generated')
    parser.add_argument('--xmax', required=True, type=float, help='easternmost longitude (west is negative)')
    parser.add_argument('--xmin', required=True, type=float, help='westernmost longitude (west is negative)')
    parser.add_argument('--ymax', required=True, type=float, help='northernmost latitude (south is negative)')
    parser.add_argument('--ymin', required=True, type=float, help='southernmost longitude (south is negative)')
    parser.add_argument('--tilesize', type=int, help='tilesize value (default %d)' % Region.tilesize)
    parser.add_argument('--scale', type=int, help='scale value (default %d)' % Region.scale)
    parser.add_argument('--vscale', type=int, help='vscale value (default %d)' % Region.vscale)
    parser.add_argument('--trim', type=int, help='trim value (default %d)' % Region.trim)
    parser.add_argument('--sealevel', type=int, help='sealevel value (default %d)' % Region.sealevel)
    parser.add_argument('--maxdepth', type=int, help='maxdepth value (default %d)' % Region.maxdepth)
    parser.add_argument('--elfiles', type=str, help='ZIP files containing elevation data retrieved from USGS')
    parser.add_argument('--lcfiles', type=str, help='ZIP files containing landcover data retrieved from USGS')
    parser.add_argument('--disable-ore', action='store_false', dest='doOre', default=True, help='disable ore generation')
    parser.add_argument('--enable-schematics', action='store_true', dest='doSchematics', default=False, help='enable schematic usage')
    parser.add_argument('--debug', action='store_true', help='enable debug output')
    args = parser.parse_args()

    # enable debug
    if (args.debug):
        # JMT: previously debug was for suds, now we no longer download files
        pass

    # create the region
    print "Creating new region %s..." % args.name
    myRegion = Region(name=args.name, xmax=args.xmax, xmin=args.xmin, ymax=args.ymax, ymin=args.ymin, scale=args.scale, vscale=args.vscale, trim=args.trim, tilesize=args.tilesize, sealevel=args.sealevel, maxdepth=args.maxdepth, lcfiles=args.lcfiles, elfiles=args.elfiles, doOre=args.doOre, doSchematics=args.doSchematics)

    print "Retrieving files..."
    myRegion.maketiffs()

if __name__ == '__main__':
    sys.exit(main())
