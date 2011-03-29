# bathy module

from numpy import zeros, uint8
from itertools import product
from random import random
from dataset import getDatasetDims
from math import hypot
import invdisttree
from mcarray import sealevel
import logging
logging.basicConfig(level=logging.WARNING)
bathylogger = logging.getLogger('bathy')

def getBathymetry(args, lcArray, bigArray, baseOffset, bigOffset):
    "Generates rough bathymetric values based on proximity to terrain.  Increase slope to decrease dropoff."
    # NB: slope not currently implemented
    # what is water?
    setWater = set([11, 12])
    # FIXME: nodata always considered water
    setWater.add(args.nodata)
    # build an lc invdisttree *without* setWater values
    bathyMaxRows, bathyMaxCols = lcArray.shape
    bigMaxRows, bigMaxCols = bigArray.shape
    xDiff = baseOffset[1]-bigOffset[1]
    zDiff = baseOffset[0]-bigOffset[0]
    bathyArray = zeros((bathyMaxRows, bathyMaxCols),dtype=uint8)
    bigDry = [[x,z] for x,z in product(xrange(bigMaxRows), xrange(bigMaxCols)) if bigArray[x,z] not in setWater]
    # if there's no land at all... 
    if (len(bigDry) == 0):
        bathyArray += args.maxdepth
        return bathyArray
    bigXValues = [x for x,z in bigDry]
    bigZValues = [z for x,z in bigDry]
    bigXIDT = invdisttree.Invdisttree(bigDry, bigXValues)
    bigZIDT = invdisttree.Invdisttree(bigDry, bigZValues)
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
            bathyArray[x-xDiff, z-zDiff] = min(args.maxdepth,hypot((bigX-x), (bigZ-z)))
    return bathyArray

def checkMaxDepth(string):
    "Checks to see if the given max depth is valid."
    # okay, 1 is a minimum and sealevel-1 is a maximum
    maxdepth = max(min(string, sealevel-1), 1)
    if (maxdepth != string):
        bathylogger.warning("Maximum depth of %d is invalid -- changed to %d" % (string, maxdepth))
    return maxdepth

def checkSlope(args):
    "Checks to see if the given slope is valid for the given region."
    if (isinstance(args.slope, list)):
        oldslope = args.slope[0]
    else:
        oldslope = int(args.slope)
    # FIXME: need better answers here, right now guessing
    extreme = 4
    slope = max(min(oldslope, extreme), 1/extreme)
    if (slope != oldslope):
        bathylogger.warning("Slope of %d for region %s is invalid -- changed to %d" % (oldslope, args.region, slope))
    args.slope = slope
    return slope

