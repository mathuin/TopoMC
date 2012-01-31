# new crust module
import numpy
from timer import timer
from itertools import product
from random import randint, uniform
from invdisttree import Invdisttree

@timer()
def getCrust(xsize, zsize):
    """Generates smoothly irregular crust layer for the tile."""
    # start with five percent coverage and a thickness between one and five blocks
    numPoints = int(xsize*zsize*0.05)
    crustshape = (zsize, xsize)
    basearray = numpy.array([(z, x) for z, x in product(xrange(zsize), xrange(xsize))])
    coordslist = numpy.array([(randint(0, zsize-1), randint(0, xsize-1)) for elem in xrange(numPoints)])
    valueslist = numpy.array([uniform(1, 5) for elem in coordslist])
    crustIDT = Invdisttree(coordslist, valueslist)
    crustarray = crustIDT(basearray, nnear=11)
    crustarray.resize(crustshape)
    return crustarray
    
