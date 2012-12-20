from helpers import load_vars_from_file, configure_cl, gen_params_from_base, chunker
from time import time
from math import sqrt
import numpy as np
import pyopencl as cl
import pyopencl.array as cla

from buildtree import buildtree
from knn import knn
from invdisttree import Invdisttree

debug = True

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
    # assuming two arrays of int32's
    bytes_per_row = ylen * nnear * 4 * 2
    real_rows_per_slice = int(0.5*gpu['device'].max_mem_alloc_size/bytes_per_row)
    # force slice to test reassembly
    num_slices = 1 # 4
    fake_rows_per_slice = int(xlen/num_slices)+1
    if real_rows_per_slice > fake_rows_per_slice:
        rows_per_slice = fake_rows_per_slice
    else:
        rows_per_slice = real_rows_per_slice
    if debug:
        print 'rows is ', xlen
        print 'rows_per_slice is ', rows_per_slice
        if rows_per_slice == fake_rows_per_slice:
            print 'NOTE: using fake instead of real to force split'

    # build everything but indices and distances and xfirst and xlen
    tree_arr = np.asarray(cpu_tree, dtype=np.uint32)
    tree_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=tree_arr)
    coords_arr = np.asarray(coords, dtype=np.float32)
    coords_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords_arr)
    lentree_arg = np.uint32(len(tree_arr))
    ink_arg = np.uint32(nnear)
    xstep_arg = np.int32(xstep)
    yfirst_arg = np.int32(yfirst)
    ylen_arg = np.int32(ylen)
    ystep_arg = np.int32(ystep)
    for slice in chunker(xrange(xfirst, xlen*xstep+xfirst, xstep), rows_per_slice):
        newxfirst = slice[0]
        newxlen = len(slice)
        if debug:
            print 'xfirst now ', newxfirst, ', xlen now ', newxlen
        lenslice = newxlen * ylen
        # now do indices and distances and xfirst and xlen
        indices_arr = np.empty(lenslice*nnear, dtype=np.uint32)
        indices_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, indices_arr.nbytes)
        # indices_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=indices_arr)
        distances_arr = np.empty(lenslice*nnear, dtype=np.float32)
        # distances_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, indices_arr.nbytes)
        distances_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=distances_arr)
        xfirst_arg = np.int32(newxfirst)
        xlen_arg = np.int32(newxlen)
        # now do event
        event = gpu['program'].knn(gpu['queue'], gpu['global_size_2d'], gpu['local_size_2d'], indices_buf, distances_buf, tree_buf, coords_buf, lentree_arg, ink_arg, xfirst_arg, xlen_arg, xstep_arg, yfirst_arg, ylen_arg, ystep_arg) 
        event.wait()
        indices_out = np.empty_like(indices_arr)
        cl.enqueue_copy(gpu['queue'], indices_out, indices_buf)
        distances_out = np.empty_like(distances_arr)
        cl.enqueue_copy(gpu['queue'], distances_out, distances_buf)
        # need to concatenate results
        if newxfirst == xfirst:
            if debug:
                print 'first pass through slices'
            gpu_indices = np.copy(indices_out)
            gpu_distances = np.copy(distances_out)
        else:
            if debug:
                print 'concatenation'
                print gpu_indices.shape, indices_out.shape
                print gpu_distances.shape, distances_out.shape
            gpu_indices = np.concatenate((gpu_indices, indices_out))
            gpu_distances = np.concatenate((gpu_distances, distances_out))
    ctime2 = time()
    cdelta = ctime2-ctime1
    print '... finished in ', cdelta, 'seconds!'
    # finding KNN with CPU
    print 'finding ', nnear, 'nearest neighbors with CPU'
    btime1 = time()
    #results = knn(cpu_tree, coords, nnear, xfirst, xlen, xstep, yfirst, ylen, ystep)
    IDT = Invdisttree(coords, values)
    #results = np.asarray(IDT(ARG, nnear, majority=(usemajority==1)), dtype=np.int32)
    cpu_distances, cpu_indices = np.asarray(IDT.distances(base, nnear))
    btime2 = time()
    bdelta = btime2-btime1
    print '... finished in ', bdelta, 'seconds!'
    # time to compare results
    # first convert to tuples
    cpu_results = [ sorted([(int(cpu_indices[ind][x]), float("%.4f" % cpu_distances[ind][x])) for x in xrange(cpu_distances.shape[1])], key = lambda elem: (elem[1], elem[0])) for ind in xrange(cpu_distances.shape[0]) ]
    gpu_results = [ sorted([(gpu_indices[ind+x*lenresults], float("%.4f" % gpu_distances[ind+x*lenresults])) for x in xrange(nnear)], key = lambda elem: (elem[1], elem[0])) for ind in xrange(lenresults) ]
    # compare
    nomatch = 0
    if not all(cpu_results[x] == gpu_results[x] for x in xrange(lenresults)):
        for x in xrange(lenresults):
            if (cpu_results[x] != gpu_results[x]):
                if (cpu_results[x][-1][0] != gpu_results[x][-1][0] and cpu_results[x][-1][1] == gpu_results[x][-1][1]):
                    continue
                else:
                    nomatch += 1
                    if nomatch < 10:
                        print 'no match at ', x, ' base: ', base[x]
                        print ' CPU: ', cpu_results[x]
                        print ' GPU: ', gpu_results[x]
        print nomatch, 'of', lenresults, 'failed to match non-trivially'
        raise AssertionError

if __name__ == '__main__':
    # run some tests here
    #testknn('Tiny-a.pkl')
    #testknn('LessTiny-a.pkl')
    #testknn('EvenLessTiny-a.pkl')
    testknn('Tiny-b.pkl')
    #testknn('LessTiny-b.pkl')
    #testknn('EvenLessTiny-b.pkl')
