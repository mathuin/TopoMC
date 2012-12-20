from helpers import load_vars_from_file, configure_cl, chunker
from time import time
import numpy as np
import pyopencl as cl
import pyopencl.array as cla

from buildtree import buildtree
from knn import knn
from invdisttree import Invdisttree

debug = False

def testknn(filename=None, num_slices=1):
    print 'testknn %s %d' % (filename, num_slices)
    (coords, values, base, nnear, usemajority, oldretval) = load_vars_from_file(filename)
    lenbase = len(base)
    # building tree with CPU
    print 'building tree with CPU'
    atime1 = time()
    cpu_tree = buildtree(coords)
    atime2 = time()
    adelta = atime2-atime1
    print '... finished in ', adelta, 'seconds!'
    # now finding KNN with GPU
    gpu = configure_cl('knn.cl', 1)
    # create buffers and arguments
    print 'finding ', nnear, 'nearest neighbors with GPU'
    ctime1 = time()
    # build everything but indices and distances and base
    tree_arr = np.asarray(cpu_tree, dtype=np.uint32)
    tree_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=tree_arr)
    coords_arr = np.asarray(coords, dtype=np.float32)
    coords_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords_arr)
    lentree_arg = np.uint32(len(tree_arr))
    ink_arg = np.uint32(nnear)
    # for each base value (float2) there are nnear index and distance (float32)
    bytes_per_elem = 8+8*nnear
    real_elems_per_slice = int(0.5*gpu['device'].max_mem_alloc_size/bytes_per_elem)
    # force slice to test reassembly
    fake_elems_per_slice = int(lenbase/num_slices)+1
    if real_elems_per_slice > fake_elems_per_slice:
        elems_per_slice = fake_elems_per_slice
    else:
        elems_per_slice = real_elems_per_slice
    if debug:
        print 'elems is ', lenbase
        print 'elems_per_slice is ', elems_per_slice
        if elems_per_slice == fake_elems_per_slice:
            print 'NOTE: using fake instead of real to force split'
    # iterate through slices
    gpu_results = []
    for chunk in chunker(base, elems_per_slice):
        lenchunk = len(chunk)
        # now do indices and distances and base (oh my!)
        indices_arr = np.empty(lenchunk*nnear, dtype=np.uint32)
        indices_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, indices_arr.nbytes)
        distances_arr = np.empty(lenchunk*nnear, dtype=np.float32)
        distances_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=distances_arr)
        # this must be split properly later
        chunk_arr = np.asarray(chunk, dtype=np.float32)
        chunk_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=chunk_arr)
        lenchunk_arg = np.uint32(lenchunk)
        # now do event
        event = gpu['program'].knnbase(gpu['queue'], gpu['global_size_1d'], gpu['local_size_1d'], indices_buf, distances_buf, tree_buf, coords_buf, lentree_arg, chunk_buf, lenchunk_arg, ink_arg)
        event.wait()
        #indices_out = np.empty_like(indices_arr)
        cl.enqueue_copy(gpu['queue'], indices_arr, indices_buf)
        #distances_out = np.empty_like(distances_arr)
        cl.enqueue_copy(gpu['queue'], distances_arr, distances_buf)
        # need to concatenate results
        raw_results = [ sorted([(int(indices_arr[ind+x*lenchunk]), float("%.4f" % distances_arr[ind+x*lenchunk])) for x in xrange(nnear)], key = lambda elem: (elem[1], elem[0])) for ind in xrange(lenchunk) ]
        if gpu_results == []:
            gpu_results = raw_results
        else:
            gpu_results += raw_results
    ctime2 = time()
    cdelta = ctime2-ctime1
    print '... finished in ', cdelta, 'seconds!'
    # finding KNN with CPU
    print 'finding ', nnear, 'nearest neighbors with CPU'
    btime1 = time()
    IDT = Invdisttree(coords, values)
    #results = np.asarray(IDT(ARG, nnear, majority=(usemajority==1)), dtype=np.int32)
    cpu_distances, cpu_indices = np.asarray(IDT.distances(base, nnear))
    cpu_results = [ sorted([(int(cpu_indices[ind][x]), float("%.4f" % cpu_distances[ind][x])) for x in xrange(cpu_distances.shape[1])], key = lambda elem: (elem[1], elem[0])) for ind in xrange(cpu_distances.shape[0]) ]
    btime2 = time()
    bdelta = btime2-btime1
    print '... finished in ', bdelta, 'seconds!'
    # time to compare results
    nomatch = 0
    for x in xrange(lenbase):
        if not all(cpu_results[x][n][1] == gpu_results[x][n][1] for n in xrange(nnear)):
            nomatch += 1
            if nomatch < 10:
                print 'no match at ', x, ' base: ', base[x]
                print ' CPU: ', cpu_results[x]
                print ' GPU: ', gpu_results[x]
    if nomatch > 0:
        print nomatch, 'of', lenbase, 'failed to match non-trivially'
        raise AssertionError

if __name__ == '__main__':
    # run some tests here
    testknn('Tiny-a.pkl',1)
    testknn('LessTiny-a.pkl',2)
    testknn('EvenLessTiny-a.pkl',3)
    testknn('Tiny-b.pkl',1)
    testknn('LessTiny-b.pkl',2)
    testknn('EvenLessTiny-b.pkl',3)
