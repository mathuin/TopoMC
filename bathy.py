# bathy module

from numpy import zeros, uint8, transpose, nonzero, array
from numpy.linalg import norm
from itertools import product
from random import random
from dataset import getDatasetDims

useNew = True

def getBathymetry(lcArray, maxDepth, slope=1):
    "Generates rough bathymetric values based on proximity to terrain.  Increase slope to decrease dropoff."
    bathyMaxRows, bathyMaxCols = lcArray.shape
    bathyArray = zeros((bathyMaxRows, bathyMaxCols),dtype=uint8)
    for brow, bcol in product(xrange(bathyMaxRows), xrange(bathyMaxCols)):
        if (lcArray[brow,bcol] == 11):
            bxmin = max(0, brow-1)
            bxmax = min(bathyMaxRows,brow+2)
            bzmin = max(0, bcol-1)
            bzmax = min(bathyMaxCols,bcol+1)
            barray = bathyArray[bathyArray[bxmin:bxmax,bzmin:bzmax].flatten().nonzero()]
            #if (all(element == 0 for element in bathyList)):
            if (len(barray) == 0):
                ringrange = xrange(1,maxDepth)
            else:
                ringrange = xrange(barray.min()-1,min(barray.max()+2, maxDepth))
            try:
                for ring in ringrange:
                    rbxmin = max(0, brow-ring+1)
                    rbxmax = min(bathyMaxRows, brow+ring+1)
                    rbzmin = max(0, bcol-ring+1)
                    rbzmax = min(bathyMaxCols, bcol+ring+1)
                    ringarray = lcArray[rbxmin:rbxmax,rbzmin:rbzmax].flatten()
                    # if (any(element != 11 for element in ringarray)):
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

