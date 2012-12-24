# Inverse distance tree -- OpenCL and cKDTree both
from __future__ import division
import numpy as np
from scipy.spatial import cKDTree as KDTree
from math import log

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
            raise AssertionError, "lencoords does not equal lenvalues"

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
                    self.local_size[device] = (work_group_size, )
                    self.global_size[device] = (num_groups_for_1d * work_group_size,  )
                self.canCL = True
            # FIXME: Use an exception type here.
            except:
                print 'warning: unable to use pyopencl, defaulting to cKDTree'

        if self.canCL:
            self.tree = self.buildtree()
        else:
            self.tree = KDTree(coords)

    def __call__(self, base, nnear=None, majority=True):
        """
        For each query point in the base array, find the K nearest
        neighbors and calculate either the majority value or the
        inverse-weighted value for those neighbors.

        Keyword arguments:
        base -- output array (x, y)
        nnear -- number of neighbors to check
        majority -- boolean: whether to use the majority algorithm

        """
        # set nearest neighbors to default value of 11 if not set
        if nnear == None:
            nnear = 11
        if self.canCL and self.wantCL:
            lenbase = len(base)
            base_arr = np.asarray(base, dtype=np.float32)
            # These values do not change from run to run.
            values_buf = cla.to_device(self.queue, self.values)
            tree_buf = cla.to_device(self.queue, self.tree)
            coords_buf = cla.to_device(self.queue, self.coords)
            lentree_arg = np.uint32(len(self.tree))
            nnear_arg = np.uint32(nnear)
            usemajority_arg = np.uint32(1 if majority else 0)
            # Calculate how many base element can be evaluated per run.
            static_data = self.values.nbytes + self.tree.nbytes + self.coords.nbytes + lentree_arg.nbytes + nnear_arg.nbytes + usemajority_arg.nbytes
            # Each base element is two float32's and its retval is one int32.
            bytes_per_elem_single = 2*4
            bytes_per_elem_total = bytes_per_elem_single + 4
            # Check both single and total limits.
            elems_per_slice_single = [int(0.95*device.max_mem_alloc_size/bytes_per_elem_single) for device in self.devices]
            elems_per_slice_total = [int(0.95*device.global_mem_size-static_data/bytes_per_elem_total) for device in self.devices]
            elem_limits = [elems_per_slice_single[x] if elems_per_slice_single[x]<elems_per_slice_total[x] else elems_per_slice_total[x] for x in xrange(len(self.devices))]
            # For now, at least, do not create retval or chunk buffer here.
            results = []
            # NB: Only supporting one device for now.
            best_device = np.argmax(elem_limits)
            for chunk in self.chunks(base_arr, elem_limits[best_device]):
                # Create retvals and chunk buffer here instead of above.
                lenchunk = len(chunk)
                retvals_arr = np.empty(lenchunk, dtype=np.int32)
                retvals_buf = cla.to_device(self.queue, retvals_arr)
                chunk_buf = cla.to_device(self.queue, chunk)
                lenchunk_arg = np.uint32(lenchunk)
                event = self.program.idt(self.queue, self.global_size[self.devices[best_device]], self.local_size[self.devices[best_device]], retvals_buf.data, values_buf.data, tree_buf.data, coords_buf.data, lentree_arg, chunk_buf.data, lenchunk_arg, nnear_arg, usemajority_arg)
                event.wait()
                # cl.enqueue_copy(self.queue, retvals_arr, retvals_buf)
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
                    w = 1/dist
                    w /= np.sum(w)
                    if majority:
                        majordict = dict([(x, 0) for x in self.values[ix]])
                        for zval, wval in zip(self.values[ix], w):
                            majordict[zval] += wval
                        wz = max(majordict, key=majordict.get)
                    else:
                        wz = np.dot(w, self.values[ix])
                results[jinterpol] = wz
                jinterpol += 1
        return np.asarray(results)

    @staticmethod
    def chunks(data, chunksize=100):
        """Overly-simple chunker..."""
        intervals = range(0, data.size, chunksize) + [None]
        for start, stop in zip(intervals[:-1], intervals[1:]):
            yield np.array(data[start:stop])

    def buildtree(self):
        # initialize tree and stack
        tree = np.empty(len(self.coords)+1, dtype=np.uint32)
        tree[0] = 0
        stack = []
        
        # seed stack
        initial_indices = np.array([x for x in xrange(self.coords.shape[0])])
        initial_axis = 0
        initial_location = 1
        stack.append((initial_indices, initial_axis, initial_location))
    
        # work through stack
        while (len(stack) > 0):
            (indices, axis, location) = stack.pop()
            # if location is out of bounds, freak out
            if (location < 1 or location > len(tree)):
                raise IndexError, 'bad location: %d' % location
            # if only one index, we are a leaf
            if (len(indices) == 1):
                tree[location] = indices[0]
                continue
            # generate sorted index of array 
            splitarr = np.hsplit(self.coords[indices], 2)
            newindices = np.lexsort((splitarr[1-axis].flatten(), splitarr[axis].flatten()))
            # now calculate n, m, and r
            n = len(newindices)
            m = int(2**(int(log(n,2))))
            r = n-(m-1)
            # median?
            if (r <= (m/2)):
                median = (m-2)/2+r+1
            else:
                median = (m-2)/2+m/2+1
            tree[location] = indices[newindices[median-1]]
            if (median > 0):
                stack.append((indices[newindices[:median-1]], 1-axis, location*2))
            if (median < len(indices)):
                stack.append((indices[newindices[median:]], 1-axis, location*2+1))

        # return the tree
        return tree

