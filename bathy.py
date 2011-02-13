# bathy module

from numpy import zeros, uint8
from itertools import product
from random import random
from dataset import getDatasetDims

useNew = True

def getBathymetry(lcArray, bigArray, baseOffset, bigOffset, maxDepth, slope=1):
    "Generates rough bathymetric values based on proximity to terrain.  Increase slope to decrease dropoff."
    # FIXME: eventually support ice as well as water here
    bathyMaxRows, bathyMaxCols = lcArray.shape
    bigMaxRows, bigMaxCols = bigArray.shape
    xDiff = baseOffset[1]-bigOffset[1]
    zDiff = baseOffset[0]-bigOffset[0]
    bathyArray = zeros((bathyMaxRows, bathyMaxCols),dtype=uint8)
    ringrange = xrange(1,maxDepth)
    for brow, bcol in product(xrange(bathyMaxRows), xrange(bathyMaxCols)):
        if (lcArray[brow,bcol] == 11):
            try:
                for ring in ringrange:
                    rbxmin = max(0, (brow-ring+1)+xDiff)
                    rbxmax = min(bigMaxRows, (brow+ring+1)+xDiff)
                    rbzmin = max(0, (bcol-ring+1)+zDiff)
                    rbzmax = min(bigMaxCols, (bcol+ring+1)+zDiff)
                    ringarray = bigArray[rbxmin:rbxmax,rbzmin:rbzmax].flatten()
                    if any(ringarray != 11):
                        raise Exception
            except Exception:
                pass
            if (random() > 1/slope):
                ring = ring + 1
            bathyArray[brow,bcol] = ring
    return bathyArray

def checkMaxDepth(args):
    "Checks to see if the given max depth is valid for the given region."
    if (isinstance(args.maxdepth, list)):
        oldmaxdepth = args.maxdepth[0]
    else:
        oldmaxdepth = int(args.maxdepth)
    (rows, cols) = getDatasetDims(args.region)
    # okay, 1 is a minimum
    # rows/cols is a max
    maxdepth = max(1, oldmaxdepth)
    maxdepth = min(maxdepth, min(rows, cols))
    if (maxdepth != oldmaxdepth):
        print "Warning: maximum depth of %d for region %s is invalid -- changed to %d" % (oldmaxdepth, args.region, maxdepth)
    args.maxdepth = maxdepth
    return maxdepth

def checkSlope(args):
    "Checks to see if the given slope is valid for the given region."
    if (isinstance(args.slope, list)):
        oldslope = args.slope[0]
    else:
        oldslope = int(args.slope)
    # FIXME: need better answers here, right now guessing
    extreme = 4
    slope = min(oldslope, extreme)
    slope = max(slope, 1/extreme)
    if (slope != oldslope):
        print "Warning: maximum depth of %d for region %s is invalid -- changed to %d" % (oldslope, args.region, slope)
    args.slope = slope
    return slope

