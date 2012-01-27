#!/usr/bin/env python

from newregion import Region
from newutils import ds
import sys
import argparse
import logging

def checkElevationIDs(string):
    """Checks to see if the given product IDs are valid."""
    givenIDs = string.split(',')
    validIDs = [ ID for ID in givenIDs if ID in Region.productIDs['elevation'] ]
    if validIDs == givenIDs:
        return givenIDs
    else:
        raise argparse.ArgumentTypeError, 'elevation IDs invalid: %s' % string

def checkLandcoverIDs(string):
    """Checks to see if the given product IDs are valid."""
    givenIDs = string.split(',')
    validIDs = [ ID for ID in givenIDs if ID in Region.productIDs['landcover'] ]
    if validIDs == givenIDs:
        return givenIDs
    else:
        raise argparse.ArgumentTypeError, 'landcover IDs invalid: %s' % string

def main(argv):
    """Creates a specified region and downloads files from USGS."""
    # example:
    # ./GetRegion.py --name BlockIsland --ymax 41.2378 --ymin 41.1415 --xmin -71.6202 --xmax -71.5332

    # defaults
    default_elevationIDs = ','.join(Region.productIDs['elevation'])
    default_landcoverIDs = ','.join(Region.productIDs['landcover'])

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
    parser.add_argument('--elevationIDs', default=default_elevationIDs, type=checkElevationIDs, help='ordered list of product IDs (default %s)' % default_elevationIDs)
    parser.add_argument('--landcoverIDs', default=default_landcoverIDs, type=checkLandcoverIDs, help='ordered list of product IDs (default %s)' % default_landcoverIDs)
    parser.add_argument('--debug', action='store_true', help='enable debug output')
    args = parser.parse_args()

    # enable debug
    if (args.debug):
        logging.getLogger('suds.client').setLevel(logging.DEBUG)

    # create the region
    print "Creating new region %s..." % args.name
    myRegion = Region(name=args.name, xmax=args.xmax, xmin=args.xmin, ymax=args.ymax, ymin=args.ymin, scale=args.scale, vscale=args.vscale, trim=args.trim, tilesize=args.tilesize, sealevel=args.sealevel, maxdepth=args.maxdepth, lcIDs=args.landcoverIDs, elIDs=args.elevationIDs)

    # temporary
    if (args.debug):
        print "For scale %d, the region you have selected will have origin %d x %d and size %d x %d" % (myRegion.scale, myRegion.txmin*myRegion.tilesize, myRegion.tymin*myRegion.tilesize, (myRegion.txmax-myRegion.txmin)*myRegion.tilesize, (myRegion.tymax-myRegion.tymin)*myRegion.tilesize)

    print "Downloading files..."
    myRegion.getfiles()
    if (args.debug):
        lcds = ds(myRegion.mapfile(myRegion.lclayer))
        print "The landcover file has dimensions %d x %d" % (lcds.RasterXSize, lcds.RasterYSize)
        elds = ds(myRegion.mapfile(myRegion.ellayer))
        print "The elevation file has dimensions %d x %d" % (elds.RasterXSize, elds.RasterYSize)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

