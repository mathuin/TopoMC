# Inverse distance tree -- OpenCL and cKDTree both
from __future__ import division
import numpy as np
from scipy.spatial import cKDTree as KDTree
from time import time
from utils import chunks, buildtree
from itertools import product
#
import gzip
import cPickle as pickle

try:
    import pyopencl as cl
    import pyopencl.array as cla
    hasCL = True
except ImportError:
    hasCL = False


class idt:

    def __init__(self, coords, values, wantCL=True, platform_num=None):
        """
        Take the coordinates and values and build a KD tree.

        Keyword arguments:
        coords -- input coordinates (x, y)
        values -- input values

        """

        self.coords = np.asarray(coords, dtype=np.float32)
        self.values = np.asarray(values, dtype=np.int32)

        if self.coords.shape[0] != self.values.shape[0]:
            raise AssertionError('lencoords does not equal lenvalues')

        self.wantCL = wantCL
        self.canCL = False

        if hasCL and self.wantCL:
            try:
                platforms = cl.get_platforms()
                try:
                    platform = platforms[platform_num]
                    self.devices = self.platform.get_devices()
                    self.context = cl.Context(self.devices)
                except TypeError:
                    # The user may be asked to select a platform.
                    self.context = cl.create_some_context()
                    self.devices = self.context.devices
                except IndexError:
                    raise
                self.queue = cl.CommandQueue(self.context)
                filestr = ''.join(open('idt.cl', 'r').readlines())
                self.program = cl.Program(self.context, filestr).build(devices=self.devices)
                for device in self.devices:
                    buildlog = self.program.get_build_info(device, cl.program_build_info.LOG)
                    if (len(buildlog) > 1):
                        print 'Build log for device', device, ':\n', buildlog
                # Only the first kernel is used.
                self.kernel = self.program.all_kernels()[0]

                # Local and global sizes are device-dependent.
                self.local_size = {}
                self.global_size = {}
                # Groups should be overcommitted.
                # For now, use 3 (48 cores / 16 cores per halfwarp) * 2
                for device in self.devices:
                    work_group_size = self.kernel.get_work_group_info(cl.kernel_work_group_info.WORK_GROUP_SIZE, device)
                    num_groups_for_1d = device.max_compute_units * 3 * 2
                    self.local_size[device] = (work_group_size,)
                    self.global_size[device] = (num_groups_for_1d * work_group_size,)
                self.canCL = True
            # FIXME: Use an exception type here.
            except:
                print 'warning: unable to use pyopencl, defaulting to cKDTree'

        if self.canCL:
            self.tree = buildtree(coords)
        else:
            self.tree = KDTree(coords)

    def __call__(self, base, shape, nnear=None, majority=True, pickle_name=None):
        """
        For each query point in the base array, find the K nearest
        neighbors and calculate either the majority value or the
        inverse-weighted value for those neighbors.

        Keyword arguments:
        base -- output array (x, y)
        nnear -- number of neighbors to check
        majority -- boolean: whether to use the majority algorithm
        pickle -- boolean: save variables for pickling

        """
        # Set nearest neighbors to default value of 11 if not set.
        if nnear is None:
            nnear = 11

        if self.canCL and self.wantCL:
            # These values do not change from run to run.
            values_buf = cla.to_device(self.queue, self.values)
            tree_buf = cla.to_device(self.queue, self.tree)
            coords_buf = cla.to_device(self.queue, self.coords)
            lentree_arg = np.uint32(len(self.tree))
            nnear_arg = np.uint32(nnear)
            usemajority_arg = np.uint32(1 if majority else 0)
            # Calculate how many base elements can be evaluated per run.
            static_data = self.values.nbytes + self.tree.nbytes + self.coords.nbytes + lentree_arg.nbytes + nnear_arg.nbytes + usemajority_arg.nbytes
            # Each base element is two float32s (8 bytes).
            bpe_single = 2*4
            # Each retval is one int32 (4 bytes).
            bpe_total = bpe_single + 4
            # Check both single and total limits for elems-per-slice.
            eps_single = [int(0.95*device.max_mem_alloc_size/bpe_single) for device in self.devices]
            eps_total = [int((0.95*device.global_mem_size-static_data)/bpe_total) for device in self.devices]
            elem_limits = [min(eps_single[x], eps_total[x]) for x in xrange(len(self.devices))]
            # For now, at least, do not create retval or chunk buffer here.
            results = []
            # NB: Only supporting one device for now.
            best_device = np.argmax(elem_limits)
            global_size = self.global_size[self.devices[best_device]]
            local_size = self.local_size[self.devices[best_device]]
            for chunk in chunks(base, elem_limits[best_device]):
                # Create retvals and chunk buffer here instead of above.
                lenchunk = len(chunk)
                retvals_arr = np.empty(lenchunk, dtype=np.int32)
                retvals_buf = cla.to_device(self.queue, retvals_arr)
                chunk_buf = cla.to_device(self.queue, chunk)
                lenchunk_arg = np.uint32(lenchunk)
                event = self.program.idt(self.queue, global_size, local_size, retvals_buf.data, values_buf.data, tree_buf.data, coords_buf.data, lentree_arg, chunk_buf.data, lenchunk_arg, nnear_arg, usemajority_arg)
                event.wait()
                # Copy retvals_buf to results.
                retvals_arr = retvals_buf.get()
                if results == []:
                    results = retvals_arr.tolist()
                else:
                    results += retvals_arr.tolist()
        else:
            # from invdisttree.py
            distances, indexes = self.tree.query(base, k=nnear)
            results = np.zeros((len(distances),) + np.shape(self.values[0]))
            jinterpol = 0
            for distance, index in zip(distances, indexes):
                if nnear == 1:
                    wz = self.values[index]
                elif distance[0] < 1e-10:
                    wz = self.values[index[0]]
                else:
                    w = 1/distance
                    w /= np.sum(w)
                    if majority:
                        majordict = dict([(x, 0) for x in self.values[index]])
                        for zval, wval in zip(self.values[index], w):
                            majordict[zval] += wval
                        wz = max(majordict, key=majordict.get)
                    else:
                        wz = np.dot(w, self.values[index])
                results[jinterpol] = wz
                jinterpol += 1
        if pickle_name is not None:
            # Pickle variables for testing purposes.
            picklefilename = 'idt-%s-%d.pkl.gz' % (pickle_name, (1 if majority else 0))
            print 'Pickling to %s...' % picklefilename
            f = gzip.open(picklefilename, 'wb')
            pickle.dump(self.coords, f, -1)
            pickle.dump(self.values, f, -1)
            pickle.dump(base, f, -1)
            pickle.dump(shape, f, -1)
            pickle.dump(nnear, f, -1)
            pickle.dump(majority, f, -1)
            # pickle.dump(results, f, -1)
        return np.asarray(results, dtype=np.uint32).reshape(shape)

    @staticmethod
    def test(fileobj, image=False):
        # Import from pickled variables for now.
        jar = gzip.GzipFile(fileobj=fileobj)
        coords = pickle.load(jar)
        values = pickle.load(jar)
        base = pickle.load(jar)
        shape = pickle.load(jar)
        nnear = pickle.load(jar)
        usemajority = pickle.load(jar)
        jar.close()
        lenbase = len(base)

        print 'Generating results with OpenCL'
        atime1 = time()
        gpu_idt = idt(coords, values, wantCL=True)
        if gpu_idt.canCL is False:
            raise AssertionError('Cannot run test without working OpenCL')
        gpu_results = gpu_idt(base, shape, nnear=nnear, majority=(usemajority == 1))
        atime2 = time()
        adelta = atime2-atime1
        print '... finished in ', adelta, 'seconds!'

        print 'Generating results with cKDTree'
        btime1 = time()
        cpu_idt = idt(coords, values, wantCL=False)
        cpu_results = cpu_idt(base, shape, nnear=nnear, majority=(usemajority == 1))
        btime2 = time()
        bdelta = btime2-btime1
        print '... finished in ', bdelta, 'seconds!'

        # Compare the results.
        allowed_error_percentage = 1
        maxnomatch = int(allowed_error_percentage*0.01*lenbase)
        xlen, ylen = gpu_results.shape
        if image:
            print 'Generating image of differences'
            import re
            import Image
            imagefile = re.sub('pkl.gz', 'png', fileobj.name)
            # diffarr = (cpu_results + 128 - gpu_results).astype(np.int32)
            diffarr = np.array([[int(128 + cpu_results[x, y] - gpu_results[x, y]) for y in xrange(ylen)] for x in xrange(xlen)], dtype=np.int32)
            Image.fromarray(diffarr).save(imagefile)
        else:
            nomatch = sum([1 if abs(cpu_results[x, y] - gpu_results[x, y]) > 0.0001 else 0 for x, y in product(xrange(xlen), xrange(ylen))])
            if nomatch > maxnomatch:
                countprint = 0
                for x, y in product(xrange(xlen), xrange(ylen)):
                    if abs(cpu_results[x, y] - gpu_results[x, y]) > 0.0001:
                        countprint += 1
                        if countprint < 10:
                            print "no match at ", x, y
                            print " CPU: ", cpu_results[x, y]
                            print " GPU: ", gpu_results[x, y]
                        else:
                            break
                raise AssertionError('%d of %d (%d%%) failed to match' % (nomatch, lenbase, 100*nomatch/lenbase))
            else:
                print '%d of %d (%d%%) failed to match' % (nomatch, lenbase, 100*nomatch/lenbase)

if __name__ == '__main__':
    import argparse
    import glob

    parser = argparse.ArgumentParser(description='Test IDT functionality with OpenCL and cKDTree/Invdisttree.')
    parser.add_argument('files', type=argparse.FileType('r'), nargs='*',
                        help='a data file to be processed')
    parser.add_argument('--image', action='store_true',
                        help='generate an image with the differences')

    args = parser.parse_args()
    if (args.files == []):
        args.files = [open(file) for file in glob.glob('./idt-*.pkl.gz')]
    for testfile in args.files:
        print 'Testing %s' % testfile.name
        idt.test(testfile, image=args.image)
        testfile.close()
