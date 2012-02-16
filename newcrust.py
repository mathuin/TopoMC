# new crust module
from itertools import product
from random import randint, uniform
from newcl import CL

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
        self.coords = [(randint(0, self.zsize-1), randint(0, self.xsize-1)) for elem in xrange(self.numcoords)]
        self.values = [uniform(Crust.minwidth, Crust.maxwidth) for elem in xrange(self.numcoords)]
        self.base = [(z, x) for z, x in product(xrange(self.zsize), xrange(self.xsize))]
        self.cl = CL(self.coords, self.values, self.base, wantCL=self.wantCL, majority=False)

    def __call__(self):
        retval = self.cl()
        retval.resize((self.zsize, self.xsize))
        return retval

if __name__ == '__main__':
    xsize = 1536
    zsize = 2048
    print 'initializing Crust object with size %d, %d with OpenCL wanted' % (xsize, zsize) 
    yes = Crust(xsize, zsize, wantCL=True)
    print 'initializing Crust object with size %d, %d with OpenCL unwanted' % (xsize, zsize) 
    no = Crust(xsize, zsize, wantCL=False)
    print 'creating Crust via OpenCL with OpenCL wanted...'
    yes()
    print 'creating Crust via Invdisttree with OpenCL wanted...'
    yes(useCL=False)
    print 'creating Crust via Invdisttree with OpenCL unwanted...'
    no()
    print 'deleting old object'
    del yes
    print 'initializing Crust object with size %d, %d with OpenCL wanted' % (xsize, zsize) 
    yes = Crust(xsize, zsize, wantCL=True)
    print 'creating Crust via OpenCL with OpenCL wanted...'
    yes()


