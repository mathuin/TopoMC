from helpers import load_vars_from_file, configure_cl, gen_params_from_base, chunker
from time import time
import numpy as np
import pyopencl as cl
import pyopencl.array as cla
from collections import Counter
from invdisttree import Invdisttree

from buildtree import buildtree

def testidt(filename=None, num_slices=1):
    print 'testidt %s %d' % (filename, num_slices)
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
    gpu = configure_cl('idt.cl', 1)
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
    # for each base value (float2) there is one retval (int32)
    bytes_per_elem_single = 4*2
    bytes_per_elem_total = 4*2+4
    static_data = values_arr.nbytes + tree_arr.nbytes + coords_arr.nbytes
    # based on single memory allocation
    real_elems_per_slice_single = int(0.95*gpu['device'].max_mem_alloc_size/bytes_per_elem_single)
    real_elems_per_slice_global = int(0.95*(gpu['device'].global_mem_size-static_data)/bytes_per_elem_total)
    if (real_elems_per_slice_single > real_elems_per_slice_global):
        print 'using global value: ', real_elems_per_slice_global
        real_elems_per_slice = real_elems_per_slice_global
    else:
        print 'using single value: ', real_elems_per_slice_single
        real_elems_per_slice = real_elems_per_slice_single
    # force slice to test reassembly
    fake_elems_per_slice = int(lenbase/num_slices)+1
    if real_elems_per_slice > fake_elems_per_slice:
        elems_per_slice = fake_elems_per_slice
        print 'using fake elems per slice: ', fake_elems_per_slice
    else:
        elems_per_slice = real_elems_per_slice
        print 'using real elems per slice: ', real_elems_per_slice
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
        # print "global size: ", gpu['global_size_1d']
        # print "local size: ", gpu['local_size_1d']
        # print "max mem alloc size: ", gpu['device'].max_mem_alloc_size
        # print "global mem size: ", gpu['device'].global_mem_size
        # print "retvals size: ", retvals_buf.size
        # print "values size: ", values_buf.size
        # print "tree size: ", tree_buf.size
        # print "coords size: ", coords_buf.size
        # print "chunk size: ", chunk_buf.size
        # print "total: ", retvals_buf.size+values_buf.size+tree_buf.size+coords_buf.size+chunk_buf.size
        event = gpu['program'].idt(gpu['queue'], gpu['global_size_1d'], gpu['local_size_1d'], retvals_buf, values_buf, tree_buf, coords_buf, lentree_arg, chunk_buf, lenchunk_arg, ink_arg, usemajority_arg)
        event.wait()
        cl.enqueue_copy(gpu['queue'], retvals_arr, retvals_buf)
        # print Counter(retvals_arr)
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
            if nomatch < 0:
                print 'no match at ', x
                print ' CPU: ', cpu_results[x]
                print ' GPU: ', gpu_results[x]
    if nomatch > 0:
        print nomatch, 'of', lenbase, 'failed to match'
        # raise AssertionError

if __name__ == '__main__':
    # run some tests here
    # testidt('Tiny-a.pkl.gz')
    # testidt('LessTiny-a.pkl.gz')
    # testidt('EvenLessTiny-a.pkl.gz')
    # testidt('Tiny-b.pkl.gz')
    # testidt('LessTiny-b.pkl.gz')
    # testidt('EvenLessTiny-b.pkl.gz')
    testidt('BlockIsland-a.pkl.gz')
    testidt('BlockIsland-b.pkl.gz')
    # testidt('CratersOfTheMoon-a.pkl.gz')
    # testidt('CratersOfTheMoon-b.pkl.gz')
