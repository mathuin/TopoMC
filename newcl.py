# new CL module
from numpy import asarray, array, int32, zeros, empty_like
import numpy
from timer import timer
from itertools import product
from random import randint, uniform
from invdisttree import Invdisttree
from multiprocessing import Pool
try:
    import pyopencl as cl
except ImportError:
    pass

class CL:
    """Use OpenCL or Invdisttree to solve the IDT problem."""

    # value at which tests show performance decreases as arrays grow
    IDTmaxsize = 2048
    # value at which video card refuses to run while X is on
    OpenCLmaxsize = 512

    # default value for nearest neighbors
    nnear = 11

    @timer()
    def genindices(self, arrayin):
        """Generate indices for splitting array."""
        retval = dict()
        # splitting is harder than I thought.
        for index, elem in enumerate(arrayin):
            splitkey = tuple([int(x/self.split) for x in elem],)
            try:
                retval[splitkey]
            except KeyError:
                retval[splitkey] = []
            retval[splitkey].append(index)
        return retval

    @timer()
    def __init__(self, coords, values, base, wantCL=True, split=None, nnear=None, majority=True):
        self.coords = asarray(coords, dtype=int32)
        self.values = asarray(values, dtype=int32)
        self.base = asarray(base, dtype=int32)
        (lencoords, null) = self.coords.shape
        (lenvalues,) = self.values.shape
        (lenbase, null) = self.base.shape
        assert lencoords == lenvalues, "lencoords does not equal lenvalues"
        
        self.wantCL = wantCL
        if self.wantCL == True:
            if split == None:
                self.split = CL.OpenCLmaxsize
            else:
                self.split = split
            try:
                self.ctx = cl.create_some_context()
                self.queue = cl.CommandQueue(self.ctx)
                filestr = ''.join(open('nearest.cl', 'r').readlines())
                self.program = cl.Program(self.ctx, filestr).build()
                self.coordindices = self.genindices(self.coords)
                self.baseindices = self.genindices(self.base)
                self.canCL = True
            except:
                # prolly should be specific here
                print "warning: unable to import pyopencl, defaulting to Invdisttree"
                self.canCL = False

        if nnear == None:
            self.nnear = CL.nnear
        else:
            self.nnear = nnear

        if majority == True:
            self.usemajority = 1
        else:
            self.usemajority = 0

    def build(self, coords, values, base):
        (lenbase, null) = base.shape
        (lencoords, null) = coords.shape
        template = zeros((lenbase), dtype=int32)
        coords_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords)
        values_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=values)
        base_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=base)
        template_buf = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, size=template.nbytes)
        self.program.nearest(self.queue, base.shape, None, coords_buf, values_buf, base_buf, template_buf, int32(lencoords), int32(self.nnear), int32(self.usemajority))
        suboutput = empty_like(template)
        cl.enqueue_copy(self.queue, suboutput, template_buf)

        return suboutput

    @timer()
    def __call__(self):
        # build output array
        if self.wantCL and self.canCL:
            (lenbase, null) = self.base.shape
            retval = zeros((lenbase), dtype=int32)
            for key, value in self.baseindices.items():
                (a, b) = key
                cindices = []
                # currently grabs nine bins for each processed bin
                pairs = [(c, d) for c, d in product(xrange(a-1,a+2), xrange(b-1,b+2)) if (c,d) in self.coordindices.keys()]
                for pair in pairs:
                    cindices += self.coordindices[pair]
                bindices = self.baseindices[key]
                coords = self.coords[cindices]
                values = self.values[cindices]
                base = self.base[value]
                retval[value] = self.build(coords, values, base)
        else:
            IDT = Invdisttree(self.coords, self.values)
            retval = asarray(IDT(self.base, self.nnear, majority=(self.usemajority==1)), dtype=int32)
        return retval

    def __del__(self):
        self.program = None
        self.queue = None
        self.ctx = None
    

if __name__ == '__main__':
    # on my system, 2048 is faster unsplit but 4096 is faster split
    # for CL, 1024 is the largest that'll run while the video card is on
    print 'setting up CL arrays'
    xsize = 2048
    zsize = 2048
    coverage = 0.05
    numcoords = int(xsize*zsize*coverage)
    shape = (zsize, xsize)
    base = array([(z, x) for z, x in product(xrange(zsize), xrange(xsize))], dtype=int32)
    coords = array([(randint(0, zsize-1), randint(0, xsize-1)) for elem in xrange(numcoords)], dtype=int32)
    values = array([uniform(CL.minwidth, CL.maxwidth) for elem in xrange(numcoords)], dtype=int32)
    
    print 'initializing CL object of size %d, %d with (forced) splitting...' % (xsize, zsize) 
    yes = CL(coords, values, base, split=xsize)
    print 'initializing CL object of size %d, %d without splitting...' % (xsize, zsize) 
    print ' ... must disable openCL for this!'
    no = CL(coords, values, base, split=xsize, wantCL=False)
    print 'creating split CL via OpenCL...'
    yes()
    print 'cannot create unsplit CL via OpenCL as OpenCL was disabled...'
    print 'creating unsplit CL via Invdisttree...'
    no()

