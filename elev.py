# Elevation transformation -- OpenCL and numpy both
from __future__ import division
import numpy as np
from time import time
from utils import chunks
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

class elev:
    def __init__(self, elarray, wantCL=True, platform_num=None):
        """
        Take the elevation array as generated by GDAL.

        Keyword arguments:
        elarray -- array of elevation values

        """

        self.elarray = elarray

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
                filestr = ''.join(open('elev.cl', 'r').readlines())
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
                    self.local_size[device] = (work_group_size, )
                    self.global_size[device] = (num_groups_for_1d * work_group_size,  )
                self.canCL = True
            # FIXME: Use an exception type here.
            except:
                print 'warning: unable to use pyopencl, defaulting to numpy'

    def __call__(self, trim, vscale, sealevel, pickle_vars=False):
        """
        Shoehorn the array into the range required by Minecraft.

        trim -- range between sea level and minimum elevation
                to be removed
        vscale -- vertical scale
        sealevel -- Minecraft level corresponding to zero elevation
        pickle -- boolean: save variables for pickling

        """
        if self.canCL and self.wantCL:
            elarray_arr = np.asarray(self.elarray.flatten(), dtype=np.int32)
            # These values do not change from run to run.
            trim_arg = np.int32(trim)
            vscale_arg = np.int32(vscale)
            sealevel_arg = np.int32(sealevel)
            # Calculate how many retval elements can be evaluated per run.
            static_data = trim_arg.nbytes + vscale_arg.nbytes + sealevel_arg.nbytes
            # Each retval element is one int32 and its original value is one int32.
            bytes_per_elem_single = 4
            bytes_per_elem_total = bytes_per_elem_single + 4
            elems_per_slice_single = [int(0.95*device.max_mem_alloc_size/bytes_per_elem_single) for device in self.devices]
            elems_per_slice_total = [int(0.95*device.global_mem_size-static_data/bytes_per_elem_total) for device in self.devices]
            elem_limits = [elems_per_slice_single[x] if elems_per_slice_single[x]<elems_per_slice_total[x] else elems_per_slice_total[x] for x in xrange(len(self.devices))]
            # For now, at least, do not create retval or chunk buffer here.
            results = []
            # NB: Only supporting one device for now.
            best_device = np.argmax(elem_limits)
            for chunk in chunks(elarray_arr, elem_limits[best_device]):
                # Create retvals and chunk buffer here instead of above.
                lenchunk = len(chunk)
                retvals_arr = np.empty(lenchunk, dtype=np.int32)
                retvals_buf = cla.to_device(self.queue, retvals_arr)
                chunk_buf = cla.to_device(self.queue, chunk)
                lenchunk_arg = np.uint32(lenchunk)
                event = self.program.elev(self.queue, self.global_size[self.devices[best_device]], self.local_size[self.devices[best_device]], retvals_buf.data, chunk_buf.data, lenchunk_arg, trim_arg, vscale_arg, sealevel_arg)
                event.wait()
                # cl.enqueue_copy(self.queue, retvals_arr, retvals_buf)
                retvals_arr = retvals_buf.get()
                if results == []:
                    results = retvals_arr.tolist()
                else:
                    results += retvals_arr.tolist()
        else:
            results = ((self.elarray.flatten() - trim)/vscale)+sealevel
        if pickle_vars:
            # Pickle variables for testing purposes.
            print 'Pickling...'
            f = gzip.open('elev-%d-%d.pkl.gz' % (self.elarray.shape[0], self.elarray.shape[1]), 'wb')
            pickle.dump(self.elarray, f, -1)
            pickle.dump(trim, f, -1)
            pickle.dump(vscale, f, -1)
            pickle.dump(sealevel, f, -1)
            # pickle.dump(results, f, -1)
        return np.asarray(results, dtype=np.int32).reshape(self.elarray.shape)

    @staticmethod
    def test(filename=None):
        # Import from pickled variables for now.
        jar = gzip.open(filename, 'r')
        elarray = pickle.load(jar)
        trim = pickle.load(jar)
        vscale = pickle.load(jar)
        sealevel = pickle.load(jar)
        jar.close()
        lenelarray = elarray.size

        print 'Generating results with OpenCL'
        atime1 = time()
        gpu_elev = elev(elarray, wantCL=True)
        if gpu_elev.canCL == False:
            raise AssertionError, 'Cannot run test without working OpenCL'
        gpu_results = gpu_elev(trim, vscale, sealevel, pickle_vars=False)
        atime2 = time()
        adelta = atime2-atime1
        print '... finished in ', adelta, 'seconds!'

        print 'Generating results with numpy'
        btime1 = time()
        cpu_elev = elev(elarray, wantCL=False)
        cpu_results = cpu_elev(trim, vscale, sealevel, pickle_vars=False)
        btime2 = time()
        bdelta = btime2-btime1
        print '... finished in ', bdelta, 'seconds!'

        # Compare the results.
        allowed_error_percentage = 1
        maxnomatch = int(allowed_error_percentage*0.01*lenelarray)
        xlen, ylen = gpu_results.shape
        nomatch = sum([1 if cpu_results[x,y] != gpu_results[x,y] else 0 for x, y in product(xrange(xlen), xrange(ylen))])
        if nomatch > maxnomatch:
            print nomatch, 'of', lenelarray, 'failed to match'
            raise AssertionError
        else:
            print 'less than %d%% failed to match' % allowed_error_percentage
        
if __name__ == '__main__':
    # Block Island test data
    elev.test('elev-BlockIsland.pkl.gz')
    # elev.test('elev-CratersOfTheMoon.pkl.gz')
