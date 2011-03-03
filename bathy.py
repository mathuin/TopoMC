# bathy module

from numpy import zeros, uint8
from itertools import product
from random import random
from dataset import getDatasetDims
from terrain import nodata
from math import hypot
from invdisttree import Invdisttree
from mcarray import sealevel

# constants
maxdepth = 48
slope = 1

def checkMaxdepth(string):
    global maxdepth
    "Checks to see if the given max depth is valid for the given region."
    curmaxdepth = maxdepth
    oldmaxdepth = int(string)
    (rows, cols) = getDatasetDims(args.region)
    # okay, 1 is a minimum
    # rows/cols is a max
    # actually sealevel-1 is a real max! :-)
    curmaxdepth = max(1, oldmaxdepth)
    curmaxdepth = min(curmaxdepth, min(rows, cols, sealevel-1))
    if (curmaxdepth != oldmaxdepth):
        print "Warning: maximum depth of %d is invalid -- changed to %d" % (oldmaxdepth, curmaxdepth)
    maxdepth = curmaxdepth
    return maxdepth

def checkSlope(string):
    "Checks to see if the given slope is valid for the given region."
    global slope
    curslope = slope
    oldslope = int(string)
    # FIXME: need better answers here, right now guessing
    extreme = 4
    curslope = min(oldslope, extreme)
    curslope = max(curslope, 1/extreme)
    if (curslope != oldslope):
        print "Warning: maximum depth of %d is invalid -- changed to %d" % (oldslope, curslope)
    slope = curslope
    return slope

def getBathymetry(lcArray, bigArray, baseOffset, bigOffset):
    "Generates rough bathymetric values based on proximity to terrain.  Increase slope to decrease dropoff."
    # what is water?
    setWater = set([11, 12])
    if (nodata in setWater):
        setWater.update([127])
    # build an lc invdisttree *without* setWater values
    bathyMaxRows, bathyMaxCols = lcArray.shape
    bigMaxRows, bigMaxCols = bigArray.shape
    xDiff = baseOffset[1]-bigOffset[1]
    zDiff = baseOffset[0]-bigOffset[0]
    bathyArray = zeros((bathyMaxRows, bathyMaxCols),dtype=uint8)
    bigDry = [[x,z] for x,z in product(xrange(bigMaxRows), xrange(bigMaxCols)) if bigArray[x,z] not in setWater]
    # if there's no land at all... 
    if (len(bigDry) == 0):
        bathyArray += maxdepth
        return bathyArray
    bigXValues = [x for x,z in bigDry]
    bigZValues = [z for x,z in bigDry]
    bigXIDT = Invdisttree(bigDry, bigXValues)
    bigZIDT = Invdisttree(bigDry, bigZValues)
    bigFull = [[x,z] for x,z in product(xrange(bigMaxRows), xrange(bigMaxCols))]
    bigXNear = bigXIDT(bigFull, nnear=1, eps=0.1, majority=False)
    bigXNear.resize(bigArray.shape)
    bigZNear = bigZIDT(bigFull, nnear=1, eps=0.1, majority=False)
    bigZNear.resize(bigArray.shape)
    bigDepth = zeros((bigMaxRows, bigMaxCols), dtype=uint8)
    for x, z in product(xrange(xDiff,bathyMaxRows+xDiff), xrange(zDiff,bathyMaxCols+zDiff)):
        if lcArray[x-xDiff, z-zDiff] in setWater:
            bigX = bigXNear[x, z]
            bigZ = bigZNear[x, z]
            bathyArray[x-xDiff, z-zDiff] = min(maxdepth,hypot((bigX-x), (bigZ-z)))
    return bathyArray
