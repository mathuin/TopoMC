# this module is for the "crust" layer above the stone

from __future__ import division
from dataset import getDatasetDims, getDataset
from coords import getLatLongArray
from invdisttree import Invdisttree
from itertools import product
from numpy import array, int32, fromfunction, uint8, max, min
from random import randint, uniform
from time import clock

crustIDT = None

# first generate the crust IDT for the whole map
def makeCrustIDT(args):
    rows, cols = getDatasetDims(args.region)
    lcds, elevds = getDataset(args.region)
    global crustIDT
    start = clock()
    crustCoordsList = []
    crustValuesList = []
    print "making Crust IDT"
    # trying ten percent since one seemed too lame
    worldLatLong = getLatLongArray(lcds, (0, 0), (rows, cols), 1)
    crustCoordsList = [worldLatLong[randint(0,rows-1)*cols+randint(0,cols-1)] for elem in xrange(int(rows*cols*0.01))]
    crustValuesList = [uniform(1,5) for elem in crustCoordsList]
    crustIDT = Invdisttree(array(crustCoordsList), array(crustValuesList))
    print "... done in %.2f seconds" % (clock()-start)

# construct the crust array for the tile
def getCrust(bathyArray, baseArray):
    "Get crust array."
    crustArray = crustIDT(baseArray, nnear=11)
    return crustArray
    
    
    

