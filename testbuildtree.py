from helpers import load_vars_from_file, configure_cl, gen_params_from_base
from time import time
import numpy as np
import pyopencl as cl
import pyopencl.array as cla

from buildtree import buildtree, printtree

# this script tests the buildtree.cl code against the buildtree.py code
# the buildtree.cl code has not yet been written
# the buildtree.py code generates the trees we use for later tests

def testbuildtree(filename=None):
    print 'testbuildtree %s' % filename
    print 'GPU HAS NOT YET BEEN IMPLEMENTED'
    (coords, values, base, nnear, usemajority, oldretval) = load_vars_from_file(filename)
    # now build with GPU
    gpu = configure_cl('buildtree.cl')
    # create buffers and arguments
    print 'building tree with GPU'
    btime1 = time()
    coords_arr = np.asarray(coords, dtype=np.int32)
    lencoords = len(coords)
    tree_arr = np.empty(lencoords+1, dtype=np.uint32)
    tree_buf = cl.Buffer(gpu['context'], cl.mem_flags.WRITE_ONLY, tree_arr.nbytes)
    coords_buf = cl.Buffer(gpu['context'], cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=coords_arr)
    lencoords_arg = np.uint32(lencoords)
    event = gpu['program'].buildtree(gpu['queue'], gpu['global_size_1d'], gpu['local_size_1d'], tree_buf, coords_buf, lencoords_arg)
    event.wait()
    tree_out = np.empty_like(tree_arr)
    cl.enqueue_copy(gpu['queue'], tree_out, tree_buf)
    tree_out[0] = 0
    btime2 = time()
    bdelta = btime2-btime1
    print '... finished in ', bdelta, 'seconds!'
    # build with CPU
    print 'building tree with CPU'
    atime1 = time()
    cpu_tree = buildtree(coords)
    atime2 = time()
    adelta = atime2-atime1
    print '... finished in ', adelta, 'seconds!'
    # need comparison
    printtree(cpu_tree, coords)
    # if true, return tree
    return cpu_tree

if __name__ == '__main__':
    # run some tests here
    testbuildtree('Tiny-a.pkl.gz')
    #testbuildtree('LessTiny-a.pkl.gz')
    #testbuildtree('EvenLessTiny-a.pkl.gz')
    #testbuildtree('Tiny-b.pkl.gz')
    #testbuildtree('LessTiny-b.pkl.gz')
    #testbuildtree('EvenLessTiny-b.pkl.gz')
