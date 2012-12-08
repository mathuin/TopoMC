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
        # first, run the 'mmd' program
        if False:
            (minx, maxx, dupx, miny, maxy, dupy, arraylen) = self.minmaxdup(arrayin)
            # only change split if interval is equal
            # interval equation is (maxx-minx+1)/dupy and vice versa
            # cross multiplying avoid integer division crazy
            rangex = maxx-minx+1
            rangey = maxy-miny+1
            intx = rangex*dupx
            inty = rangey*dupy
            if (intx == inty):
                print "X: range = %d, dup = %d" % (rangex, dupy)
                print "X: range = %d, dup = %d" % (rangey, dupx)
                self.split = self.device.max_work_group_size*rangex/dupy
                print "Split: %d" % self.split
        # run the 'trim' program
        # see mmd for why these are good parameters
        num_groups = self.device.max_compute_units * 3 * 2
        local_size = self.device.max_work_group_size
        global_size = num_groups * local_size
        trim_global_size = (global_size,)
        trim_local_size = (local_size,)
        # need to split if it's too long!
        indexmaxsize = self.device.global_mem_size/16 # 2 int2's each
        splitlist = tuple([x for x in xrange(indexmaxsize, arrayin.shape[0], indexmaxsize)])
        indexinc = 0
        for chunk in np.vsplit(arrayin, splitlist):
            chunkarr = cla.to_device(self.queue, np.asarray(chunk, dtype=np.int32))
            template = cla.empty_like(chunkarr)
            event = self.program.trim(self.queue, trim_global_size, trim_local_size, chunkarr.data, template.data, np.int32(self.split), np.int32(len(chunk)))
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
            indexinc += indexmaxsize
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
            # try:
            self.platform = cl.get_platforms()[0]
            self.device = self.platform.get_devices()[0]
            self.context = cl.Context([self.device])
            self.queue = cl.CommandQueue(self.context)
            filestr = ''.join(open('idt.cl', 'r').readlines())
            self.program = cl.Program(self.context, filestr).build()
            self.coordindices = self.genindices(self.coords)
            self.baseindices = self.genindices(self.base)
            self.canCL = True
            # # FIXME: specify an exception type
            # except:
            #     print "warning: unable to use pyopencl, defaulting to Invdisttree"
            #     self.canCL = False
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

    def minmaxdup(self, arrayin):
        """Use OpenCL to calculate minimum, maximum, and number of duplicates."""
        # JMT: begin insanity
        # FIXME: add a flag here for crust stuff to not use it
        # it's not necessary or relevant with random values
        # how many work groups do I want
        # 3 is from 48 cores / 16 cores per halfwarp
        # 2 is for overcommitting
        num_groups = self.device.max_compute_units * 3 * 2
        # let's ask histogram book
        # how big do I want these work groups to be
        # let's set it to the max (was 256)
        local_size = self.device.max_work_group_size
        # so that makes global size the product of the above
        global_size = num_groups * local_size
        # create arrayin
        arrayin_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=arrayin)
        # create global arrays
        globalout_len = num_groups
        globalout_arr = np.zeros((globalout_len,1), dtype=np.int32)
        gminx_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, globalout_arr.nbytes)
        gmaxx_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, globalout_arr.nbytes)
        gdupx_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, globalout_arr.nbytes)
        gminy_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, globalout_arr.nbytes)
        gmaxy_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, globalout_arr.nbytes)
        gdupy_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, globalout_arr.nbytes)
        # allocate local memory
        lminx_arg = cl.LocalMemory(4*local_size)
        lmaxx_arg = cl.LocalMemory(4*local_size)
        ldupx_arg = cl.LocalMemory(4*local_size)
        lminy_arg = cl.LocalMemory(4*local_size)
        lmaxy_arg = cl.LocalMemory(4*local_size)
        ldupy_arg = cl.LocalMemory(4*local_size)
        # create constants
        arrayinlen = len(arrayin)
        arrayinlen_arg = np.uint32(arrayinlen)
        checkx = arrayin[0][0]
        checky = arrayin[0][1]
        checkx_arg = np.uint32(checkx)
        checky_arg = np.uint32(checky)
        # set sizes
        mmd_global_size = (global_size,)
        mmd_local_size = (local_size,)
        print "starting event with %d elements..." % arrayinlen
        print " - global size = ", global_size
        print " - elements per work item = ", arrayinlen/global_size
        event = self.program.mmd(self.queue, mmd_global_size, mmd_local_size, arrayin_buf, gminx_buf, gmaxx_buf, gdupx_buf, gminy_buf, gmaxy_buf, gdupy_buf, lminx_arg, lmaxx_arg, ldupx_arg, lminy_arg, lmaxy_arg, ldupy_arg, arrayinlen_arg, checkx_arg, checky_arg)
        event.wait()
        gminx_out = np.empty_like(globalout_arr)
        cl.enqueue_copy(self.queue, gminx_out, gminx_buf)
        gmaxx_out = np.empty_like(globalout_arr)
        cl.enqueue_copy(self.queue, gmaxx_out, gmaxx_buf)
        gdupx_out = np.empty_like(globalout_arr)
        cl.enqueue_copy(self.queue, gdupx_out, gdupx_buf)
        gminy_out = np.empty_like(globalout_arr)
        cl.enqueue_copy(self.queue, gminy_out, gminy_buf)
        gmaxy_out = np.empty_like(globalout_arr)
        cl.enqueue_copy(self.queue, gmaxy_out, gmaxy_buf)
        gdupy_out = np.empty_like(globalout_arr)
        cl.enqueue_copy(self.queue, gdupy_out, gdupy_buf)
        # FIXME: eventually get reduction kernel to do this!
        cgminx = min(gminx_out)
        cgmaxx = max(gmaxx_out)
        cgdupx = sum(gdupx_out)
        cgminy = min(gminy_out)
        cgmaxy = max(gmaxy_out)
        cgdupy = sum(gdupy_out)
        #print "cgminx: %d, cgminy: %d" % (cgminx, cgminy)
        #print "cgmaxx: %d, cgmaxy: %d" % (cgmaxx, cgmaxy)
        #print "cgdupx: %d, cgdupy: %d" % (cgdupx, cgdupy)
        #xarr, yarr = zip(*arrayin)
        #print "cminx: %d, cminy: %d" % (min(xarr), min(yarr))
        #print "cmaxx: %d, cmaxy: %d" % (max(xarr), max(yarr))
        #print "cdupx: %d, cdupy: %d" % (list(xarr).count(checkx), list(yarr).count(checky))
        # number of dups in X direction = number unique Y values
        return cgminx, cgmaxx, cgdupx, cgminy, cgmaxy, cgdupy, arrayinlen
        # JMT: end insanity

