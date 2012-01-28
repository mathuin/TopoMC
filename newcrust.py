# new crust module
import numpy
from itertools import product
from random import randint, uniform
from invdisttree import Invdisttree

def getCrust(tilesize):
    """Generates smoothly irregular crust layer for the tile."""
    # start with five percent
    numPoints = int(tilesize*tilesize*0.05)
    crustshape = (tilesize, tilesize)
    basearray = numpy.array([(x, y) for x, y in product(xrange(tilesize), xrange(tilesize))])
    coordslist = numpy.array([(randint(0, tilesize-1), randint(0, tilesize-1)) for elem in xrange(numPoints)])
    valueslist = numpy.array([uniform(1, 5) for elem in coordslist])
    crustIDT = Invdisttree(coordslist, valueslist)
    crustarray = crustIDT(basearray, nnear=11)
    crustarray.resize(crustshape)
    return crustarray
    
