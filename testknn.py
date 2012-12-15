from helpers import load_vars_from_file, configure_cl, gen_params_from_base, chunker
from time import time
import numpy as np
import pyopencl as cl
import pyopencl.array as cla

from buildtree import buildtree
from knn import knn

def testknn(filename=None):
    print 'testknn %s' % filename
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
    gpu = configure_cl('knn.cl')
    # create buffers and arguments
    print 'finding ', nnear, 'nearest neighbors with GPU'
    ctime1 = time()
    lenresults = xlen*ylen
    # how many bytes are in a row
    bytes_per_row = ylen * nnear * 4 * 2
    rows_per_slice = int(0.5*gpu['device'].max_mem_alloc_size/bytes_per_row)
    print 'rows is ', xlen
    print 'rows_per_slice is ', rows_per_slice
    num_slices = 4
    print 'test num_slices = ', num_slices
    rows_per_slice = int(xlen/num_slices)+1
    print 'fake rows_per_slice is ', rows_per_slice
    # build everything but indices and distances and xfirst and xlen
    tree_arr = np.asarray(cpu_tree, dtype=np.uint32)
    tree_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=tree_arr)
    coords_arr = np.asarray(coords, dtype=np.int32)
    coords_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords_arr)
    lentree_arg = np.uint32(len(tree_arr))
    k_arg = np.uint32(nnear)
    xstep_arg = np.int32(xstep)
    yfirst_arg = np.int32(yfirst)
    ylen_arg = np.int32(ylen)
    ystep_arg = np.int32(ystep)
    for slice in chunker(xrange(xfirst, xlen*xstep+xfirst, xstep), rows_per_slice):
        newxfirst = slice[0]
        newxlen = len(slice)
        print 'xfirst now ', xfirst, ', xlen now ', xlen
        lenslice = newxlen * ylen
        # now do indices and distances and xfirst and xlen
        indices_arr = np.empty(lenslice*nnear, dtype=np.uint32)
        indices_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, indices_arr.nbytes)
        # indices_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=indices_arr)
        distances_arr = np.empty(lenslice*nnear, dtype=np.uint32)
        # distances_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, indices_arr.nbytes)
        distances_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=distances_arr)
        xfirst_arg = np.int32(newxfirst)
        xlen_arg = np.int32(newxlen)
        # now do event
        event = gpu['program'].knn(gpu['queue'], gpu['global_size_2d'], gpu['local_size_2d'], indices_buf, distances_buf, tree_buf, coords_buf, lentree_arg, k_arg, xfirst_arg, xlen_arg, xstep_arg, yfirst_arg, ylen_arg, ystep_arg) 
        event.wait()
        indices_out = np.empty_like(indices_arr)
        cl.enqueue_copy(gpu['queue'], indices_out, indices_buf)
        distances_out = np.empty_like(distances_arr)
        cl.enqueue_copy(gpu['queue'], distances_out, distances_buf)
        # need to concatenate results
        if newxfirst == xfirst:
            print 'first pass through slices'
            bigindices = np.copy(indices_out)
            bigdistances = np.copy(distances_out)
        else:
            print 'concatenation'
            print bigindices.shape, indices_out.shape
            bigindices = np.concatenate((bigindices, indices_out))
            print bigdistances.shape, distances_out.shape
            bigdistances = np.concatenate((bigdistances, distances_out))
    ctime2 = time()
    cdelta = ctime2-ctime1
    print '... finished in ', cdelta, 'seconds!'
    # finding KNN with CPU
    print 'finding ', nnear, 'nearest neighbors with CPU'
    btime1 = time()
    results = knn(cpu_tree, coords, nnear, xfirst, xlen, xstep, yfirst, ylen, ystep)
    btime2 = time()
    bdelta = btime2-btime1
    print '... finished in ', bdelta, 'seconds!'
    # time to compare results
    # first convert to tuples
    gpu_results = [ [(bigindices[ind+x*lenresults], sqrt(bigdistances[ind+x*lenresults])) for x in xrange(nnear)] for ind in xrange(lenresults)]
    # compare
    nomatch = 0
    if not all(sorted(results[x], key = lambda elem: (elem[1], elem[0])) == sorted(gpu_results[x], key = lambda elem: (elem[1], elem[0])) for x in xrange(len(results))):
        for x in xrange(len(results)):
            if (sorted(results[x], key = lambda elem: (elem[1], elem[0])) != sorted(gpu_results[x], key = lambda elem: (elem[1], elem[0]))):
                nomatch += 1
                if nomatch < 10:
                    print 'no match at ', x 
                    print ' CPU: ', sorted(results[x], key = lambda elem: (elem[1], elem[0]))
                    print ' GPU: ', sorted(gpu_results[x], key = lambda elem: (elem[1], elem[0]))
        print nomatch, 'failed to match'
        raise AssertionError
