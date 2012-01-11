#!/usr/bin/env python

from newregion import Region
import sys
import argparse

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
    parser.add_argument('--elevationIDs', default=default_elevationIDs, type=checkElevationIDs, help='ordered list of product IDs (default %s)' % default_elevationIDs)
    parser.add_argument('--landcoverIDs', default=default_landcoverIDs, type=checkLandcoverIDs, help='ordered list of product IDs (default %s)' % default_landcoverIDs)
    parser.add_argument('--debug', action='store_true', help='enable debug output')
    args = parser.parse_args()

    # enable debug
    if (args.debug):
        logging.getLogger('suds.client').setLevel(logging.DEBUG)

    # create the region
    print "Creating new region %s..." % args.name
    myRegion = Region(name=args.name, xmax=args.xmax, xmin=args.xmin, ymax=args.ymax, ymin=args.ymin, lcIDs=args.landcoverIDs, elIDs=args.elevationIDs)

    print "Downloading files..."
    myRegion.getfiles()
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

