# crust module
from itertools import product
from random import randint, uniform
from idt import idt

class Crust:
    """Smoothly irregular crust between the surface and the underlying stone."""

    # these constants chosen by observation
    minwidth = 1
    maxwidth = 5

    def __init__(self, xsize, zsize, coverage=0.05, wantCL=True):
        self.xsize = xsize
        self.zsize = zsize
        self.coverage = coverage
        self.wantCL = wantCL
        self.numcoords = int(self.xsize * self.zsize * self.coverage)
        self.shape = (self.zsize, self.xsize)
        self.coords = [(randint(0, self.zsize-1), randint(0, self.xsize-1)) for dummy in xrange(self.numcoords)]
        self.values = [uniform(Crust.minwidth, Crust.maxwidth) for elem in xrange(self.numcoords)]
        self.base = [(z, x) for z, x in product(xrange(self.zsize), xrange(self.xsize))]
        self.idt = idt(self.coords, self.values, wantCL=self.wantCL)
        # self.clidt = CLIDT(self.coords, self.values, self.base, wantCL=self.wantCL, majority=False)

    def __call__(self):
        # retval = self.clidt()
        retval = self.idt(self.base, majority=False)
        retval.resize((self.zsize, self.xsize))
        return retval
