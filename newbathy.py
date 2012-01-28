# new bathy

from numpy import zeros, uint8
from itertools import product
from math import hypot
from invdisttree import Invdisttree

def getBathy(deptharray, tilesize, maxdepth):
    """Generates rough bathymetric values based on proximity to terrain."""
    depthshape = deptharray.shape
    depthedge = tilesize + 2 * maxdepth
    if depthshape[0] != depthedge or depthshape[1] != depthedge:
        raise AttributeError, "deptharray is wrong shape"
    setWater = set([11, 12])
    bathyarray = zeros((tilesize, tilesize), dtype=uint8)
    bigDry = [[x, z] for x, z in product(xrange(depthedge), xrange(depthedge)) if deptharray[x, z] not in setWater]
    # if no land in range at all...
    if (len(bigDry) == 0):
        bathyarray += maxdepth
        return bathyarray
    bigXValues = [x for x, z in bigDry]
    bigZValues = [z for x, z in bigDry]
    bigXIDT = Invdisttree(bigDry, bigXValues)
    bigZIDT = Invdisttree(bigDry, bigZValues)
    bigFull = [[x, z] for x, z in product(xrange(depthedge), xrange(depthedge))]
    bigXNear = bigXIDT(bigFull, nnear=1, eps=0.1)
    bigXNear.resize(depthshape)
    bigZNear = bigZIDT(bigFull, nnear=1, eps=0.1)
    bigZNear.resize(depthshape)
    # do it!
    for x, z in product(xrange(maxdepth,tilesize+maxdepth), xrange(maxdepth,tilesize+maxdepth)):
        if deptharray[x, z] in setWater:
            bigX = bigXNear[x, z]
            bigZ = bigZNear[x, z]
            bathyarray[x-maxdepth, z-maxdepth] = min(maxdepth, hypot((bigX-x), (bigZ-z)))
    return bathyarray
    

