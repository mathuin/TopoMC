import cPickle as pickle
import pyopencl as cl
import pyopencl.array as cla
from math import sqrt
from itertools import islice

def load_vars_from_file(filename):
    jar = open(filename, 'r')
    coords = pickle.load(jar)
    values = pickle.load(jar)
    base = pickle.load(jar)
    nnear = pickle.load(jar)
    usemajority = pickle.load(jar)
    #oldretval = pickle.load(jar)
    oldretval = None
    jar.close()
    return (coords, values, base, nnear, usemajority, oldretval)

def configure_cl(filename, platform_num=0):
    # initialize object
    cldict = {}
    # define basic components
    #print cl.get_platforms()
    # need 1 for Intel for printf
    cldict['platform'] = cl.get_platforms()[platform_num]
    #print cldict['platform'].get_devices()
    cldict['device'] = cldict['platform'].get_devices()[0]
    cldict['context'] = cl.Context([cldict['device']])
    cldict['queue'] = cl.CommandQueue(cldict['context'])
    # load programs
    filestr = ''.join(open(filename, 'r').readlines())
    cldict['program'] = cl.Program(cldict['context'], filestr).build(devices=[cldict['device']])
    buildlog = cldict['program'].get_build_info(cldict['device'], cl.program_build_info.LOG)
    if (len(buildlog) > 1):
        print buildlog
    # for now, assume one kernel per file -- DANGEROUS
    kernel = cldict['program'].all_kernels()[0]
    # do something smart with these eventually
    cldict['preferred_multiple'] = kernel.get_work_group_info(cl.kernel_work_group_info.PREFERRED_WORK_GROUP_SIZE_MULTIPLE, cldict['device'])
    cldict['work_group_size'] = kernel.get_work_group_info(cl.kernel_work_group_info.WORK_GROUP_SIZE, cldict['device'])
    # set parameters
    # - work groups (3 for 48 cores / 16 cores per halfwarp, 2 for overcommitting)
    num_groups_for_1d = cldict['device'].max_compute_units * 3 * 2
    num_groups_for_2d = cldict['device'].max_compute_units * 2 # * 3 * 2
    # - local size (dialed up to the max)
    local_size_for_1d = cldict['device'].max_work_group_size
    local_size_for_2d = int(sqrt(cldict['device'].max_work_group_size))
    cldict['local_size_1d'] = (local_size_for_1d, )
    cldict['local_size_2d'] = (local_size_for_2d, local_size_for_2d, )
    # - global size (just enough to keep work groups overcommitted)
    cldict['global_size_1d'] = (num_groups_for_1d * local_size_for_1d, )
    cldict['global_size_2d'] = (num_groups_for_2d * local_size_for_2d, num_groups_for_2d * local_size_for_2d, )
    # return object
    return cldict

def gen_params_from_base(base):
    # base is not what we like today
    xhash = {}
    yhash = {}
    for value in base:
        try:
            xhash[value[0]] += 1
        except KeyError:
            xhash[value[0]] = 1
        try:
            yhash[value[1]] += 1
        except KeyError:
            yhash[value[1]] = 1
    sortedxkeys = sorted(xhash.keys())
    xstart = sortedxkeys[0]
    xstop = sortedxkeys[-1]+(sortedxkeys[1]-sortedxkeys[0])
    xstep = sortedxkeys[1]-sortedxkeys[0]
    xlen = len(sortedxkeys)
    sortedykeys = sorted(yhash.keys())
    ystart = sortedykeys[0]
    ystop = sortedykeys[-1]+(sortedykeys[1]-sortedykeys[0])
    ystep = sortedykeys[1]-sortedykeys[0]
    ylen = len(sortedykeys)
    testx = [x for x in xrange(xstart, xstop, xstep)]
    if any([sortedxkeys[x] != testx[x] for x in xrange(xlen)]):
        print 'fail x'
    testy = [y for y in xrange(ystart, ystop, ystep)]
    if any([sortedykeys[y] != testy[y] for y in xrange(ylen)]):
        print 'fail y'
    return (xstart, xlen, xstep, ystart, ylen, ystep)

def chunker(iterable, chunksize):
    """
    Return elements from the iterable in `chunksize`-ed lists. The last returned
    chunk may be smaller (if length of collection is not divisible by `chunksize`).

    >>> print list(chunker(xrange(10), 3))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    """
    i = iter(iterable)
    while True:
        wrapped_chunk = [list(islice(i, int(chunksize)))]
        if not wrapped_chunk[0]:
            break
        yield wrapped_chunk.pop()

