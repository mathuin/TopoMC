# OpenCL/IDT module
import numpy as np
import sys
from itertools import product
from invdisttree import Invdisttree
try:
    import pyopencl as cl
    import pyopencl.array as cla
    hasCL = True
except ImportError:
    hasCL = False

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
        for chunk in np.vsplit(arrayin, splitlist):
            chunkarr = cla.to_device(self.queue, np.asarray(chunk, dtype=np.int32))
            template = cla.empty_like(chunkarr)
            event = self.program.trim(self.queue, chunkarr.shape, None, chunkarr.data, template.data, np.int32(self.split))
            try:
                event.wait()
            except cl.RuntimeError, inst:
                errstr = inst.__str__()
                if errstr == "clWaitForEvents failed: out of resources":
                    print 'OpenCL timed out, probably due to the display manager.'
                    print 'Disable your display manager and try again!'
                    print 'If that does not work, rerun with OpenCL disabled.'
                else:
                    raise cl.RuntimeError, inst
                sys.exit(1)

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
        self.coords = np.asarray(coords, dtype=np.int32)
        self.values = np.asarray(values, dtype=np.int32)
        self.base = np.asarray(base, dtype=np.int32)
        lencoords = self.coords.shape[0]
        lenvalues = self.values.shape[0]
        assert lencoords == lenvalues, "lencoords does not equal lenvalues"
        
        self.wantCL = wantCL
        if hasCL == True and self.wantCL == True:
            if split == None:
                self.split = CLIDT.OpenCLmaxsize
            else:
                self.split = split
            try:
                self.ctx = cl.create_some_context()
                self.queue = cl.CommandQueue(self.ctx)
                filestr = ''.join(open('idt.cl', 'r').readlines())
                self.program = cl.Program(self.ctx, filestr).build()
                self.coordindices = self.genindices(self.coords)
                self.baseindices = self.genindices(self.base)
                self.canCL = True
            # FIXME: specify an exception type
            except:
                print "warning: unable to use pyopencl, defaulting to Invdisttree"
                self.canCL = False
        else:
            self.canCL = False

        if nnear == None:
            self.nnear = np.int32(CLIDT.nnear)
        else:
            self.nnear = np.int32(nnear)

        self.usemajority = np.int32(1 if majority else 0)

    def build(self, coords, values, base):
        """Use OpenCL to build the arrays."""
        lenbase = base.shape[0]
        lencoords = coords.shape[0]
        coords_array = cla.to_device(self.queue, coords)
        values_array = cla.to_device(self.queue, values)
        base_array = cla.to_device(self.queue, base)
        template_array = cla.zeros(self.queue, (lenbase), dtype=np.int32)
        event = self.program.nearest(self.queue, base.shape, None, coords_array.data, values_array.data, base_array.data, template_array.data, np.int32(lencoords), self.nnear, self.usemajority)
        try:
            event.wait()
        except cl.RuntimeError, inst:
            errstr = inst.__str__()
            if errstr == "clWaitForEvents failed: out of resources":
                print 'OpenCL timed out, probably due to the display manager.'
                print 'Disable your display manager and try again!'
                print 'If that does not work, rerun with OpenCL disabled.'
            else:
                raise cl.RuntimeError, inst
            sys.exit(1)

        return template_array.get()

    def __call__(self):
        # build output array
        if self.wantCL and self.canCL:
            lenbase = self.base.shape[0]
            retval = np.zeros((lenbase), dtype=np.int32)
            for key, value in self.baseindices.items():
                (a, b) = key
                cindices = []
                # currently grabs nine bins for each processed bin
                pairs = [(c, d) for c, d in product(xrange(a-1, a+2), xrange(b-1, b+2)) if (c, d) in self.coordindices.keys()]
                for pair in pairs:
                    cindices += self.coordindices[pair]
                coords = self.coords[cindices]
                values = self.values[cindices]
                base = self.base[value]
                retval[value] = self.build(coords, values, base)
        else:
            IDT = Invdisttree(self.coords, self.values)
            retval = np.asarray(IDT(self.base, self.nnear, majority=(self.usemajority==1)), dtype=np.int32)
        return retval

    def __del__(self):
        self.program = None
        self.queue = None
        self.ctx = None
