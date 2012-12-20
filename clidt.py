# OpenCL/IDT module
import numpy as np
import sys
from itertools import product
from collections import Counter
from invdisttree import Invdisttree
#from crazy import k_nearest_neighbors, idw, build_tree_iter, gen_params_from_base, chunker
from helpers import gen_params_from_base, chunker
from buildtree import buildtree
from knn import knn
from idw import idw
from math import sqrt
import cPickle as pickle
from time import time
import os.path
try:
    import pyopencl as cl
    import pyopencl.array as cla
    hasCL = True
except ImportError:
    hasCL = False

class CLIDT:
    """Use OpenCL or Invdisttree to solve the IDT problem."""

    # default value for nearest neighbors
    nnear = 11

    def __init__(self, coords, values, base, wantCL=True, split=None, nnear=None, majority=True):
        self.coords = np.asarray(coords, dtype=np.int32)
        self.values = np.asarray(values, dtype=np.int32)
        # no longer care about base
        self.base = np.asarray(base, dtype=np.int32)

        lencoords = self.coords.shape[0]
        lenvalues = self.values.shape[0]
        assert lencoords == lenvalues, "lencoords does not equal lenvalues"
        
        self.wantCL = wantCL
        if hasCL == True and self.wantCL == True:
            # try:
                self.platform = cl.get_platforms()[1]
                self.device = self.platform.get_devices()[0]
                self.context = cl.Context([self.device])
                self.queue = cl.CommandQueue(self.context)
                filestr = ''.join(open('knnplus.cl', 'r').readlines())
                self.program = cl.Program(self.context, filestr).build()
                num_groups_for_1d = self.device.max_compute_units * 3 * 2
                num_groups_for_2d = self.device.max_compute_units * 2
                local_size_for_1d = self.device.max_work_group_size
                local_size_for_2d = int(sqrt(self.device.max_work_group_size))
                self.local_size_1d = (local_size_for_1d,)
                self.local_size_2d = (local_size_for_2d, local_size_for_2d,)
                self.global_size_1d = (num_groups_for_1d*local_size_for_1d,)
                self.global_size_2d = (num_groups_for_2d*local_size_for_2d, num_groups_for_2d*local_size_for_2d,)
                self.canCL = True
            # FIXME: specify an exception type
#             except:
#                print "warning: unable to use pyopencl, defaulting to Invdisttree"
#                self.canCL = False

        if nnear == None:
            self.nnear = np.int32(CLIDT.nnear)
        else:
            self.nnear = np.int32(nnear)

        self.usemajority = np.int32(1 if majority else 0)

    def __call__(self):
        # build output array
        if self.wantCL and self.canCL:
            lenbase = len(self.base)
            # building tree with CPU
            print 'building tree with CPU'
            atime1 = time()
            cpu_tree = buildtree(self.coords)
            atime2 = time()
            adelta = atime2-atime1
            print '... finished in ', adelta, 'seconds!'
            # now finding KNN with GPU
            # create buffers and arguments
            print 'finding ', self.nnear, 'nearest neighbors with GPU'
            ctime1 = time()
            # build everything but indices and distances and xfirst and xlen
            tree_arr = np.asarray(cpu_tree, dtype=np.uint32)
            tree_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=tree_arr)
            coords_arr = np.asarray(self.coords, dtype=np.float32)
            coords_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords_arr)
            values_arr = np.asarray(self.values, dtype=np.int32)
            values_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=values_arr)
            lentree_arg = np.uint32(len(tree_arr))
            ink_arg = np.uint32(self.nnear)
            usemajority_arg = np.uint32(self.usemajority)
            # each run uses values, tree, and coords
            static_data = values_arr.nbytes + tree_arr.nbytes + coords_arr.nbytes
            # each element in base requires 8 bytes for itself and 4 bytes for retval
            bytes_per_elem = 8 + 4
            elems_per_slice = int((0.5*self.device.max_mem_alloc_size-static_data)/bytes_per_elem)
            # iterate through slices
            retval = []
            for chunk in chunker(self.base, elems_per_slice):
                lenchunk = len(chunk)
                retvals_arr = np.empty(lenchunk, dtype=np.int32)
                retvals_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, retvals_arr.nbytes)
                chunk_arr = np.asarray(chunk, dtype=np.float32)
                chunk_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=chunk_arr)
                lenchunk_arg = np.uint32(lenchunk)
                # now do event
                event = self.program.knnplus(self.queue, self.global_size_1d, self.local_size_1d, retvals_buf, values_buf, tree_buf, coords_buf, lentree_arg, chunk_buf, lenchunk_arg, ink_arg, usemajority_arg)
                event.wait()
                cl.enqueue_copy(self.queue, retvals_arr, retvals_buf)
                print Counter(retvals_arr)
                # need to concatenate results
                if retval == []:
                    retval = retvals_arr.tolist()
                else:
                    retval += retvals_arr.tolist()
            ctime2 = time() 
            cdelta = ctime2-ctime1
            print '... finished in ', cdelta, 'seconds!'
        else:
            # if os.path.exists('kdtree-c.pkl'):
            #     tag = 'd'
            # elif os.path.exists('kdtree-b.pkl'):
            #     tag = 'c'
            # elif os.path.exists('kdtree-a.pkl'):
            #     tag = 'b'
            # else:
            #     tag = 'a'
            # print 'first we process'
            IDT = Invdisttree(self.coords, self.values)
            retval = IDT(self.base, self.nnear, majority=(self.usemajority==1))
            # jar = open('kdtree-%s.pkl' % tag, 'wb')
            # pickle.dump(self.coords, jar)
            # pickle.dump(self.values, jar)
            # pickle.dump(self.base, jar)
            # pickle.dump(self.nnear, jar)
            # pickle.dump(self.usemajority, jar)
            # pickle.dump(retval, jar)
            # jar.close()
            # print 'now we pickle'
        return np.asarray(retval, dtype=np.int32)

    def __del__(self):
        self.program = None
        self.queue = None
        self.ctx = None
