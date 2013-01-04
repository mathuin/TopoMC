# crust module
import numpy as np
from itertools import product
from random import randint, uniform
from idt import IDT


class Crust(object):
    """Smoothly irregular crust between the surface and the underlying stone."""

    # these constants chosen by observation
    minwidth = 1
    maxwidth = 5
    coverage = 0.05

    def __init__(self, xsize, zsize, wantCL=True):
        xsize = xsize
        zsize = zsize
        wantCL = wantCL
        numcoords = int(xsize * zsize * Crust.coverage)
        self.shape = (zsize, xsize)
        coords = np.array([(randint(0, zsize-1), randint(0, xsize-1)) for dummy in xrange(numcoords)], dtype=np.float32)
        values = np.array([uniform(Crust.minwidth, Crust.maxwidth) for elem in xrange(numcoords)], dtype=np.int32)
        self.base = np.array([(z, x) for z, x in product(xrange(zsize), xrange(xsize))], dtype=np.float32)
        self.idt = IDT(coords, values, wantCL=wantCL)

    def __call__(self, pickle_name=None):
        retval = self.idt(self.base, self.shape, majority=False, pickle_name=pickle_name)
        return retval
