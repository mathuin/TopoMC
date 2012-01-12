#!/usr/bin/env python

from newregion import Region
import sys
import argparse

from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly

def checkElevationIDs(string):
    """Checks to see if the given product IDs are valid."""
    givenIDs = string.split(',')
    validIDs = [ ID for ID in givenIDs if ID in Region.elevationIDs ]
    if validIDs == givenIDs:
        return givenIDs
    else:
        raise argparse.ArgumentTypeError, 'elevation IDs invalid: %s' % string

def checkLandcoverIDs(string):
    """Checks to see if the given product IDs are valid."""
    givenIDs = string.split(',')
    validIDs = [ ID for ID in givenIDs if ID in Region.landcoverIDs ]
    if validIDs == givenIDs:
        return givenIDs
    else:
        raise argparse.ArgumentTypeError, 'landcover IDs invalid: %s' % string

def main(argv):
    """Creates a specified region and downloads files from USGS."""
    # example:
    # ./GetRegion.py --name BlockIsland --ymax 41.2378 --ymin 41.1415 --xmin -71.6202 --xmax -71.5332

    # NB: add tile size, scale, and maxdepth here 
    # consider adding elevation and landcover ID support

    # defaults
    default_elevationIDs = ','.join(Region.elevationIDs)
    default_landcoverIDs = ','.join(Region.landcoverIDs)

    # parse options and get results
    parser = argparse.ArgumentParser(description='Create regions and download files from USGS.')
    parser.add_argument('--name', required=True, type=str, help='name of the region to be generated')
    parser.add_argument('--xmax', required=True, type=float, help='easternmost longitude (west is negative)')
    parser.add_argument('--xmin', required=True, type=float, help='westernmost longitude (west is negative)')
    parser.add_argument('--ymax', required=True, type=float, help='northernmost latitude (south is negative)')
    parser.add_argument('--ymin', required=True, type=float, help='southernmost longitude (south is negative)')
    parser.add_argument('--scale', type=int, help='scale value')
    parser.add_argument('--elevationIDs', default=default_elevationIDs, type=checkElevationIDs, help='ordered list of product IDs (default %s)' % default_elevationIDs)
    parser.add_argument('--landcoverIDs', default=default_landcoverIDs, type=checkLandcoverIDs, help='ordered list of product IDs (default %s)' % default_landcoverIDs)
    parser.add_argument('--debug', action='store_true', help='enable debug output')
    parser.add_argument('--disable-maps', action='store_false', dest='doMaps', default=True, help="disables maps retrieval when not necessary")
    args = parser.parse_args()

    # enable debug
    if (args.debug):
        logging.getLogger('suds.client').setLevel(logging.DEBUG)

    # create the region
    print "Creating new region %s..." % args.name
    myRegion = Region(name=args.name, xmax=args.xmax, xmin=args.xmin, ymax=args.ymax, ymin=args.ymin, scale=args.scale, lcIDs=args.landcoverIDs, elIDs=args.elevationIDs)

    # temporary
    print "For scale %d, the region you have selected will have origin %d x %d and size %d x %d" % (myRegion.scale, myRegion.txmin*myRegion.tilesize, myRegion.tymin*myRegion.tilesize, (myRegion.txmax-myRegion.txmin-1)*myRegion.tilesize, (myRegion.tymax-myRegion.tymin-1)*myRegion.tilesize)

    if (args.doMaps):
        print "Downloading files..."
        myRegion.getfiles()
        lcds = myRegion.ds(myRegion.lclayer)
        print "The landcover file has dimensions %d x %d" % (lcds.RasterXSize, lcds.RasterYSize)
        elds = myRegion.ds(myRegion.ellayer)
        print "The elevation file has dimensions %d x %d" % (elds.RasterXSize, elds.RasterYSize)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

