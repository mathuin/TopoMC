# Bathymetric data -- OpenCL and GDAL both
from osgeo import gdal
from utils import chunks, buildtree
from itertools import product
from time import time
import numpy as np
#
import gzip
import cPickle as pickle

try:
    import pyopencl as cl
    import pyopencl.array as cla
    hasCL = True
except ImportError:
    hasCL = False

class bathy:
    def __init__(self, lcarray, geotrans, projection, wantCL=True, platform_num=None):
        """
        Take the landcover array and GIS information.

        Keyword arguments:
        lcarray -- array of landcover values
        geotrans -- geodetic transformation
        projection -- map projection

        """
        
        self.lcarray = lcarray
        self.geotrans = geotrans
        self.projection = projection

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
                filestr = ''.join(open('bathy.cl', 'r').readlines())
                try:
                    self.program = cl.Program(self.context, filestr).build(devices=self.devices)
                except:
                    print 'problems compiling program'
                    raise
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
                print 'warning: unable to use pyopencl, defaulting to GDAL'
        if self.canCL:
            # Build coordinates and values from lcarray. 
            xlen, ylen = self.lcarray.shape
            # lcxmin = self.geotrans[0]
            # scale = self.geotrans[1]
            # lcymax = self.geotrans[3]
            # depthxrange = [lcxmin + scale * x for x in xrange(xlen)]
            # depthyrange = [lcymax - scale * y for y in xrange(ylen)]
            # rawcoords = [(x, y) for y in depthyrange for x in depthxrange]
            rawcoords = [(x, y) for y in xrange(ylen) for x in xrange(xlen)]
            # Make a tree out of non-water points.
            dryindices = np.where(self.lcarray != 11)
            # self.coords = np.array([rawcoords[dryindices[1][x]*xlen+dryindices[0][x]] for x in xrange(len(dryindices[0]))], dtype=np.float32)
            self.coords = np.array([(dryindices[1][x], dryindices[0][x]) for x in xrange(len(dryindices[0]))], dtype=np.float32)
            self.tree = buildtree(self.coords)

    def __call__(self, maxdepth, pickle_vars=True):
        """
        Traverse the landcover array.  For every point of type
        'water', calculate the distance to the nearest non-water
        point, stopping at maxdepth.

        Keyword arguments:
        maxdepth -- maximum value for depth

        """

        if self.canCL and self.wantCL:
            xlen, ylen = self.lcarray.shape
            base = np.array([(x, y) for y in xrange(maxdepth, ylen-maxdepth) for x in xrange(maxdepth, xlen-maxdepth)], dtype=np.float32)
            # These values do not change from run to run.
            tree_buf = cla.to_device(self.queue, self.tree)
            coords_buf = cla.to_device(self.queue, self.coords)
            lentree_arg = np.uint32(len(self.tree))
            maxdepth_arg = np.float32(maxdepth)
            # Calculate how many base elements can be evaluated per run.
            static_data = self.tree.nbytes + self.coords.nbytes + lentree_arg.nbytes + maxdepth_arg.nbytes
            # Each base element is two float32's and its retval is one int32.
            bytes_per_elem_single = 2*4
            bytes_per_elem_total = bytes_per_elem_single + 4
            # Check both single and total limits.
            elems_per_slice_single = [int(0.95*device.max_mem_alloc_size/bytes_per_elem_single) for device in self.devices]
            elems_per_slice_total = [int((0.95*device.global_mem_size-static_data)/bytes_per_elem_total) for device in self.devices]
            elem_limits = [elems_per_slice_single[x] if elems_per_slice_single[x]<elems_per_slice_total[x] else elems_per_slice_total[x] for x in xrange(len(self.devices))]
            # For now, at least, do not create retval or chunk buffer here.
            results = []
            # NB: Only supporting one device for now.
            best_device = np.argmax(elem_limits)
            for chunk in chunks(base, elem_limits[best_device]):
                # Create retvals and chunk buffer here instead of above.
                lenchunk = len(chunk)
                retvals_arr = np.empty(lenchunk, dtype=np.int32)
                retvals_buf = cla.to_device(self.queue, retvals_arr)
                chunk_buf = cla.to_device(self.queue, chunk)
                lenchunk_arg = np.uint32(lenchunk)
                event = self.program.bathy(self.queue, self.global_size[self.devices[best_device]], self.local_size[self.devices[best_device]], retvals_buf.data, tree_buf.data, coords_buf.data, lentree_arg, chunk_buf.data, lenchunk_arg, maxdepth_arg)
                event.wait()
                # cl.enqueue_copy(self.queue, retvals_arr, retvals_buf)
                retvals_arr = retvals_buf.get()
                if results == []:
                    results = retvals_arr.tolist()
                else:
                    results += retvals_arr.tolist()
            results = np.array(results).reshape(xlen-2*maxdepth,ylen-2*maxdepth)
        else:
            (depthz, depthx) = self.lcarray.shape
            drv = gdal.GetDriverByName('MEM')
            depthds = drv.Create('', depthx, depthz, 1, gdal.GetDataTypeByName('Byte'))
            depthds.SetGeoTransform(self.geotrans)
            depthds.SetProjection(self.projection)
            depthband = depthds.GetRasterBand(1)
            depthband.WriteArray(self.lcarray)
            # create a duplicate dataset called bathyds
            bathyds = drv.Create('', depthx, depthz, 1, gdal.GetDataTypeByName('Byte'))
            bathyds.SetGeoTransform(self.geotrans)
            bathyds.SetProjection(self.projection)
            bathyband = bathyds.GetRasterBand(1)
            # run compute proximity
            values = ','.join([str(x) for x in xrange(256) if x is not 11])
            options = ['MAXDIST=%d' % maxdepth, 'NODATA=%d' % maxdepth, 'VALUES=%s' % values]
            gdal.ComputeProximity(depthband, bathyband, options)
            # extract array
            results = bathyband.ReadAsArray(maxdepth, maxdepth, bathyds.RasterXSize-2*maxdepth, bathyds.RasterYSize-2*maxdepth)
    
        if pickle_vars:
            # Pickle variables for testing purposes.
            print 'Pickling...'
            f = gzip.open('bathy-%d-%d.pkl.gz' % (self.lcarray.shape[0], self.lcarray.shape[1]), 'wb')
            pickle.dump(self.lcarray, f, -1)
            pickle.dump(self.geotrans, f, -1)
            pickle.dump(self.projection, f, -1)
            pickle.dump(maxdepth, f, -1)
            # pickle.dump(results, f, -1)
        return np.asarray(results, dtype=np.int32).reshape(self.lcarray.shape[0]-maxdepth*2, self.lcarray.shape[1]-maxdepth*2)

    @staticmethod
    def test(filename=None):
        # Import from pickled variables for now.
        jar = gzip.open(filename, 'r')
        lcarray = pickle.load(jar)
        geotrans = pickle.load(jar)
        projection = pickle.load(jar)
        maxdepth = pickle.load(jar)
        jar.close()
        lenbase = (lcarray.shape[0]-maxdepth*2)*(lcarray.shape[1]-maxdepth*2)

        print 'Generating results with OpenCL'
        atime1 = time()
        gpu_bathy = bathy(lcarray, geotrans, projection, wantCL=True)
        print '... init took ', time()-atime1, 'seconds!'
        if gpu_bathy.canCL == False:
            raise AssertionError, 'Cannot run test without working OpenCL'
        gpu_results = gpu_bathy(maxdepth, pickle_vars=False)
        atime2 = time()
        adelta = atime2-atime1
        print '... finished in ', adelta, 'seconds!'

        print 'Generating results with numpy'
        btime1 = time()
        cpu_bathy = bathy(lcarray, geotrans, projection, wantCL=False)
        cpu_results = cpu_bathy(maxdepth, pickle_vars=False)
        btime2 = time()
        bdelta = btime2-btime1
        print '... finished in ', bdelta, 'seconds!'

        # Compare the results.
        allowed_error_percentage = 1
        maxnomatch = int(allowed_error_percentage*0.01*lenbase)
        xlen, ylen = gpu_results.shape
        nomatch = sum([1 if cpu_results[x,y] != gpu_results[x,y] else 0 for x, y in product(xrange(xlen), xrange(ylen))])
        if nomatch > maxnomatch:
            countprint = 0
            for x, y in product(xrange(xlen), xrange(ylen)):
                # if abs(cpu_results[x,y] - gpu_results[x,y]) > 2.0:
                if abs(cpu_results[x,y] - gpu_results[x,y]) > 2.0 and gpu_results[x,y] != maxdepth:
                    countprint += 1
                    if countprint < 10:
                        print "no match at ", x, y
                        print " CPU: ", cpu_results[x,y]
                        print " GPU: ", gpu_results[x,y]
                    else:
                        break

            raise AssertionError, '%d of %d failed to match' % (nomatch, lenbase)
        else:
            print 'less than %d%% failed to match' % allowed_error_percentage
        
if __name__ == '__main__':
    # Block Island test data
    bathy.test('bathy-BlockIsland.pkl.gz')
    # bathy.test('bathy-CratersOfTheMoon.pkl.gz')
