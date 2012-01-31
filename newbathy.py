# new bathy

from numpy import zeros, uint8
from itertools import product
from math import hypot
from invdisttree import Invdisttree
from timer import timer

@timer()
def getBathy(deptharray, maxdepth):
    """Generates rough bathymetric values based on proximity to terrain."""
    (depthz, depthx) = deptharray.shape
    xsize = depthx - 2 * maxdepth
    zsize = depthz - 2 * maxdepth
    setWater = set([11, 12])
    bathyarray = zeros((zsize, xsize), dtype=uint8)
    bigFull = [[z, x] for z, x in product(xrange(depthz), xrange(depthx))]
    bigDry = [[z, x] for [z, x] in bigFull if deptharray[z, x] not in setWater]
    # if no land in range at all...
    if (len(bigDry) == 0):
        bathyarray += maxdepth
        return bathyarray
    bigZValues, bigXValues = zip(*bigDry)
    bigZIDT = Invdisttree(bigDry, bigZValues)
    bigXIDT = Invdisttree(bigDry, bigXValues)
    bigZNear = bigZIDT(bigFull, nnear=1, eps=0.1)
    bigZNear.resize((depthz, depthx))
    bigXNear = bigXIDT(bigFull, nnear=1, eps=0.1)
    bigXNear.resize((depthz, depthx))
    # do it!
    for z, x in product(xrange(maxdepth,zsize+maxdepth), xrange(maxdepth,xsize+maxdepth)):
        if deptharray[z, x] in setWater:
            bigZ = bigZNear[z, x]
            bigX = bigXNear[z, x]
            bathyarray[z-maxdepth, x-maxdepth] = min(maxdepth, hypot((bigZ-z), (bigX-x)))
    return bathyarray
    

