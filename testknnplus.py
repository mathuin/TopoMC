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

def testknnplus(filename=None, num_slices=1):
    print 'testknnplus %s %d' % (filename, num_slices)
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
    gpu = configure_cl('knnplus.cl', 1)
    # create buffers and arguments
    print 'finding ', nnear, 'nearest neighbors with GPU'
    ctime1 = time()
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
    # for each base value (float2) there are nnear index and distance (float32)
    bytes_per_elem = 8+8*nnear
    real_elems_per_slice = int(0.5*gpu['device'].max_mem_alloc_size/bytes_per_elem)
    # force slice to test reassembly
    fake_elems_per_slice = int(lenbase/num_slices)+1
    if real_elems_per_slice > fake_elems_per_slice:
        elems_per_slice = fake_elems_per_slice
    else:
        elems_per_slice = real_elems_per_slice
    # iterate through slices
    gpu_results = []
    for chunk in chunker(base, elems_per_slice):
        lenchunk = len(chunk)
        retvals_arr = np.empty(lenchunk, dtype=np.int32)
        retvals_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, retvals_arr.nbytes)
        chunk_arr = np.asarray(chunk, dtype=np.float32)
        chunk_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=chunk_arr)
        lenchunk_arg = np.uint32(lenchunk)
        # now do event
        event = gpu['program'].knnplus(gpu['queue'], gpu['global_size_1d'], gpu['local_size_1d'], retvals_buf, values_buf, tree_buf, coords_buf, lentree_arg, chunk_buf, lenchunk_arg, ink_arg, usemajority_arg)
        event.wait()
        cl.enqueue_copy(gpu['queue'], retvals_arr, retvals_buf)
        print Counter(retvals_arr)
        # need to concatenate results
        if gpu_results == []:
            gpu_results = retvals_arr.tolist()
        else:
            gpu_results += retvals_arr.tolist()
    ctime2 = time()
    cdelta = ctime2-ctime1
    print '... finished in ', cdelta, 'seconds!'
    # finding KNN with CPU
    print 'finding ', nnear, 'nearest neighbors with CPU'
    ctime1 = time()
    IDT = Invdisttree(coords, values)
    cpu_results = np.asarray(IDT(base, nnear, majority=(usemajority==1)), dtype=np.int32)
    ctime2 = time()
    cdelta = ctime2-ctime1
    print '... finished in ', cdelta, 'seconds!'
    # compare
    nomatch = 0
    for x in xrange(lenbase):
        if (cpu_results[x] != gpu_results[x]):
            nomatch += 1
            if nomatch < 10:
                print 'no match at ', x
                print ' CPU: ', cpu_results[x]
                print ' GPU: ', gpu_results[x]
    if nomatch > 0:
        print nomatch, 'of', lenbase, 'failed to match'
        raise AssertionError

if __name__ == '__main__':
    # run some tests here
    # testknnplus('Tiny-a.pkl')
    # testknnplus('LessTiny-a.pkl')
    # testknnplus('EvenLessTiny-a.pkl')
    # testknnplus('Tiny-b.pkl')
    # testknnplus('LessTiny-b.pkl')
    # testknnplus('EvenLessTiny-b.pkl')
    testknnplus('BlockIsland-a.pkl')
    testknnplus('BlockIsland-b.pkl')
