from helpers import load_vars_from_file, configure_cl, gen_params_from_base, chunker
from time import time
import numpy as np
import pyopencl as cl
import pyopencl.array as cla
from collections import Counter
from invdisttree import Invdisttree

from buildtree import buildtree
# NB: not sure if knn still works!
from knn import knn
from idw import idw

def testknnplus(filename):
    print 'testknnplus %s' % filename
    (coords, values, base, nnear, usemajority, oldretval) = load_vars_from_file(filename)
    (xfirst, xlen, xstep, yfirst, ylen, ystep) = gen_params_from_base(base)
    # building tree with CPU
    print 'building tree with CPU'
    atime1 = time()
    cpu_tree = buildtree(coords)
    atime2 = time()
    adelta = atime2-atime1
    print '... finished in ', adelta, 'seconds!'
    # now finding KNN with GPU
    gpu = configure_cl('knnplus.cl')
    # create buffers and arguments
    print 'finding ', nnear, 'nearest neighbors with GPU'
    ctime1 = time()
    lenresults = xlen*ylen
    # how many bytes are in a row
    bytes_per_row = ylen * nnear * 4 * 2
    rows_per_slice = int(0.5*gpu['device'].max_mem_alloc_size/bytes_per_row)
    # print 'rows is ', xlen
    # print 'rows_per_slice is ', rows_per_slice
    num_slices = 1 # 4
    # print 'test num_slices = ', num_slices
    rows_per_slice = int(xlen/num_slices)+1
    # print 'fake rows_per_slice is ', rows_per_slice
    # build everything but indices and distances and xfirst and xlen
    tree_arr = np.asarray(cpu_tree, dtype=np.uint32)
    tree_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=tree_arr)
    coords_arr = np.asarray(coords, dtype=np.float32)
    coords_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords_arr)
    values_arr = np.asarray(values, dtype=np.int32)
    values_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=values_arr)
    lentree_arg = np.uint32(len(tree_arr))
    ink_arg = np.uint32(nnear)
    usemajority_arg = np.uint32(usemajority)
    xstep_arg = np.int32(xstep)
    yfirst_arg = np.int32(yfirst)
    ylen_arg = np.int32(ylen)
    ystep_arg = np.int32(ystep)
    for slice in chunker(xrange(xfirst, xlen*xstep+xfirst, xstep), rows_per_slice):
        newxfirst = slice[0]
        newxlen = len(slice)
        # print 'xfirst now ', newxfirst, ', xlen now ', newxlen
        lenslice = newxlen * ylen
        retvals_arr = np.empty(lenslice, dtype=np.int32)
        retvals_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, retvals_arr.nbytes)
        xfirst_arg = np.int32(newxfirst)
        xlen_arg = np.int32(newxlen)
        # now do event
        # event = gpu['program'].knnplus(gpu['queue'], gpu['global_size_2d'], gpu['local_size_2d'], retvals_buf, values_buf, tree_buf, coords_buf, lentree_arg, ink_arg, usemajority_arg, xfirst_arg, xlen_arg, xstep_arg, yfirst_arg, ylen_arg, ystep_arg) 
        # event.wait()
        # need to concatenate results
        retvals_out = np.empty_like(retvals_arr)
        cl.enqueue_copy(gpu['queue'], retvals_out, retvals_buf)
        # print Counter(retvals_out)
        if newxfirst == xfirst:
            gpu_retvals = np.copy(retvals_out)
        else:
            # print gpu_retvals.shape, retvals_out.shape
            gpu_retvals = np.concatenate((gpu_retvals, retvals_out))
    ctime2 = time()
    cdelta = ctime2-ctime1
    print '... finished in ', cdelta, 'seconds!'
    # finding KNN with CPU
    if True:
        print 'finding ', nnear, 'nearest neighbors with CPU'
        btime1 = time()
        results = knn(cpu_tree, coords, nnear, xfirst, xlen, xstep, yfirst, ylen, ystep)
        btime2 = time()
        bdelta = btime2-btime1
        print '... finished in ', bdelta, 'seconds!'
        # now performing majority on CPU
        print 'performing IDW or majority on CPU'
        ctime1 = time()
        retvals_out = np.asarray(idw(cpu_tree, values, results, usemajority), dtype=np.int32)
        ctime2 = time()
        cdelta = ctime2-ctime1
        print '... finished in ', cdelta, 'seconds!'
    if True:
        print 'yay cKDtree'
        ctime1 = time()
        IDT = Invdisttree(coords, values)
        retvals = np.asarray(IDT(base, nnear, majority=(usemajority==1)), dtype=np.int32)
        ctime2 = time()
        cdelta = ctime2-ctime1
        print '... finished in ', cdelta, 'seconds!'
    # compare
    nomatch = 0
    if not all(retvals[x] == retvals_out[x] for x in xrange(len(retvals))):
        for x in xrange(len(retvals)):
            if (retvals[x] != retvals_out[x]):
                nomatch += 1
                if nomatch < 10:
                    print 'no match at ', x
                    print ' CPU: ', retvals[x]
                    print ' GPU: ', retvals_out[x]
        print nomatch, 'failed to match'
        raise AssertionError

if __name__ == '__main__':
    # run some tests here
    testknnplus('Tiny-a.pkl')
    testknnplus('LessTiny-a.pkl')
    testknnplus('EvenLessTiny-a.pkl')
    testknnplus('Tiny-b.pkl')
    testknnplus('LessTiny-b.pkl')
    testknnplus('EvenLessTiny-b.pkl')
    testknnplus('BlockIsland-a.pkl')
    testknnplus('BlockIsland-b.pkl')
