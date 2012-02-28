# new CL IDT module
import numpy as n
from itertools import product
from random import randint, uniform
from invdisttree import Invdisttree
from multiprocessing import Pool
try:
    import pyopencl as cl
    import pyopencl.array as cla
except ImportError:
    pass

class CLIDT:
    """Use OpenCL or Invdisttree to solve the IDT problem."""

    # value at which video card refuses to run while X is on
    OpenCLmaxsize = 512
    # largest amount of indices which can be processed at once
    indexmaxsize = 8 * 1024 * 1024

    # default value for nearest neighbors
    nnear = 11

    def genindices(self, arrayin):
        """Generate indices for splitting array."""
        retval = dict()
        # run the 'trim' program
        # need to split if it's too long!
        splitlist = tuple([x for x in xrange(CLIDT.indexmaxsize, arrayin.shape[0], CLIDT.indexmaxsize)])
        indexinc = 0
        for chunk in n.vsplit(arrayin, splitlist):
            chunkarr = cla.to_device(self.queue, n.asarray(chunk, dtype=n.int32))
            template = cla.empty_like(chunkarr)
            event = self.program.trim(self.queue, chunkarr.shape, None, chunkarr.data, template.data, n.int32(self.split))
            event.wait()
            for index, elem in enumerate(template.get()):
                splitkey = tuple([x for x in elem],)
                try:
                    retval[splitkey]
                except KeyError:
                    retval[splitkey] = []
                retval[splitkey].append(index+indexinc)
            indexinc += CLIDT.indexmaxsize
        return retval

    def __init__(self, coords, values, base, wantCL=True, split=None, nnear=None, majority=True):
        self.coords = n.asarray(coords, dtype=n.int32)
        self.values = n.asarray(values, dtype=n.int32)
        self.base = n.asarray(base, dtype=n.int32)
        (lencoords, null) = self.coords.shape
        (lenvalues,) = self.values.shape
        (lenbase, null) = self.base.shape
        assert lencoords == lenvalues, "lencoords does not equal lenvalues"
        
        self.wantCL = wantCL
        if self.wantCL == True:
            if split == None:
                self.split = CLIDT.OpenCLmaxsize
            else:
                self.split = split
            try:
                import pyopencl as cl
                import pyopencl.array as cla
                self.ctx = cl.create_some_context()
                self.queue = cl.CommandQueue(self.ctx)
                filestr = ''.join(open('idt.cl', 'r').readlines())
                self.program = cl.Program(self.ctx, filestr).build()
                self.coordindices = self.genindices(self.coords)
                self.baseindices = self.genindices(self.base)
                self.canCL = True
            except ImportError:
                # prolly should be specific here
                print "warning: unable to import pyopencl, defaulting to Invdisttree"
                self.canCL = False

        if nnear == None:
            self.nnear = n.int32(CLIDT.nnear)
        else:
            self.nnear = n.int32(nnear)

        self.usemajority = n.int32(1 if majority else 0)

    def build(self, coords, values, base):
        (lenbase, null) = base.shape
        (lencoords, null) = coords.shape
        coords_array = cla.to_device(self.queue, coords)
        values_array = cla.to_device(self.queue, values)
        base_array = cla.to_device(self.queue, base)
        template_array = cla.zeros(self.queue, (lenbase), dtype=n.int32)
        event = self.program.nearest(self.queue, base.shape, None, coords_array.data, values_array.data, base_array.data, template_array.data, n.int32(lencoords), self.nnear, self.usemajority)
        event.wait()

        return template_array.get()

    def __call__(self):
        # build output array
        if self.wantCL and self.canCL:
            (lenbase, null) = self.base.shape
            retval = n.zeros((lenbase), dtype=n.int32)
            for key, value in self.baseindices.items():
                (a, b) = key
                cindices = []
                # currently grabs nine bins for each processed bin
                pairs = [(c, d) for c, d in product(xrange(a-1,a+2), xrange(b-1,b+2)) if (c,d) in self.coordindices.keys()]
                for pair in pairs:
                    cindices += self.coordindices[pair]
                coords = self.coords[cindices]
                values = self.values[cindices]
                base = self.base[value]
                retval[value] = self.build(coords, values, base)
        else:
            IDT = Invdisttree(self.coords, self.values)
            retval = n.asarray(IDT(self.base, self.nnear, majority=(self.usemajority==1)), dtype=n.int32)
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
    base = n.array([(z, x) for z, x in product(xrange(zsize), xrange(xsize))], dtype=n.int32)
    coords = n.array([(randint(0, zsize-1), randint(0, xsize-1)) for elem in xrange(numcoords)], dtype=n.int32)
    values = n.array([uniform(1, 5) for elem in xrange(numcoords)], dtype=n.int32)
    
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

