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
            except cl.RuntimeError:
                print 'warning: unable to use pyopencl, defaulting to GDAL'

    def __call__(self, maxdepth, pickle_name=None):
        """
        Traverse the landcover array.  For every point of type
        'water', calculate the distance to the nearest non-water
        point, stopping at maxdepth.

        Keyword arguments:
        maxdepth -- maximum value for depth

        """

        if self.canCL and self.wantCL:
            # Create working array
            xlen, ylen = self.lcarray.shape
            workingarr = np.array(self.lcarray.ravel(), dtype=np.int32)
            # These values do not change from run to run.
            ylen_arg = np.uint32(ylen)
            maxdepth_arg = np.uint32(maxdepth)
            # Calculate how many base elements can be evaluated per run.
            # Each run requires xlen, ylen, currdepth, and maxdepth -- all 32bit.
            static_data = 4 * 4
            # Each base element requires two 32bit integers.
            bytes_per_elem_single = 2*4
            bytes_per_elem_total = bytes_per_elem_single
            # Use rows instead of elems for two-dimensional arrays.
            bytes_per_row_single = bytes_per_elem_single * ylen
            bytes_per_row_total = bytes_per_elem_total * ylen
            # Check both single and total limits.
            rows_per_slice_single = [int(0.95*device.max_mem_alloc_size/bytes_per_row_single) for device in self.devices]
            rows_per_slice_total = [int((0.95*device.global_mem_size-static_data)/bytes_per_row_total) for device in self.devices]
            row_limits = [rows_per_slice_single[x] if rows_per_slice_single[x]<rows_per_slice_total[x] else rows_per_slice_total[x] for x in xrange(len(self.devices))]
            # NB: Only supporting one device for now.
            best_device = np.argmax(row_limits)
            best_rows = row_limits[best_device]
            # For now, at least, do not create retval or chunk buffer here.
            # Iterate through this entire mess once per depth level
            row_list = np.array([x for x in xrange(xlen)])
            negfound = False
            for row_chunk in chunks(row_list, best_rows):
                # Do not prepend buffer rows for first row.
                realfirst = row_chunk[0]
                if (row_chunk[0] != row_list[0]):
                    realfirst -= maxdepth
                # Do not postpend buffer rows for last row.
                reallast = row_chunk[-1]
                if (row_chunk[-1] != row_list[-1]):
                    reallast += maxdepth
                # Create retvals and chunk buffer here instead of above.
                chunk = np.copy(workingarr[realfirst*ylen:reallast*ylen])
                outchunk_buf = cla.empty(self.queue, chunk.shape, chunk.dtype)
                inchunk_buf = cla.to_device(self.queue, chunk)
                newxlen = reallast-realfirst
                newxlen_arg = np.uint32(newxlen)
                lenchunk = newxlen*ylen
                lenchunk_arg = np.uint32(lenchunk)
                currdepth = 0
                while (currdepth <= maxdepth):
                    currdepth_arg = np.uint32(currdepth)
                    if (currdepth % 2 == 0):
                        event = self.program.bathy(self.queue, self.global_size[self.devices[best_device]], self.local_size[self.devices[best_device]], outchunk_buf.data, inchunk_buf.data, newxlen_arg, ylen_arg, currdepth_arg, maxdepth_arg)
                    else:
                        event = self.program.bathy(self.queue, self.global_size[self.devices[best_device]], self.local_size[self.devices[best_device]], inchunk_buf.data, outchunk_buf.data, newxlen_arg, ylen_arg, currdepth_arg, maxdepth_arg)
                    event.wait()
                    currdepth += 1
                # cl.enqueue_copy(self.queue, retvals_arr, retvals_buf)
                # copy important parts of chunk_buf.data back 
                chunk_arr = outchunk_buf.get()
                copytop = 0
                if (row_chunk[0] != row_list[0]):
                    copytop += maxdepth
                copybot = len(row_chunk)-1
                workingarr[row_chunk[0]*ylen:row_chunk[-1]*ylen] = chunk_arr[copytop*ylen:copybot*ylen]
            results = workingarr.reshape((self.lcarray.shape))[maxdepth:-1*maxdepth,maxdepth:-1*maxdepth]
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
    
        if pickle_name != None:
            # Pickle variables for testing purposes.
            picklefilename = 'bathy-%s.pkl.gz' % pickle_name
            print 'Pickling to %s...' % picklefilename
            f = gzip.open(picklefilename, 'wb')
            pickle.dump(self.lcarray, f, -1)
            pickle.dump(self.geotrans, f, -1)
            pickle.dump(self.projection, f, -1)
            pickle.dump(maxdepth, f, -1)
            # pickle.dump(results, f, -1)
        return results

    @staticmethod
    def test(fileobj, image=False):
        # Import from pickled variables for now.
        jar = gzip.GzipFile(fileobj=fileobj)
        lcarray = pickle.load(jar)
        geotrans = pickle.load(jar)
        projection = pickle.load(jar)
        maxdepth = pickle.load(jar)
        jar.close()
        lenbase = (lcarray.shape[0]-maxdepth*2)*(lcarray.shape[1]-maxdepth*2)

        print 'Generating results with OpenCL'
        atime1 = time()
        gpu_bathy = bathy(lcarray, geotrans, projection, wantCL=True)
        if gpu_bathy.canCL == False:
            raise AssertionError, 'Cannot run test without working OpenCL'
        gpu_results = gpu_bathy(maxdepth)
        atime2 = time()
        adelta = atime2-atime1
        print '... finished in ', adelta, 'seconds!'

        print 'Generating results with GDAL'
        btime1 = time()
        cpu_bathy = bathy(lcarray, geotrans, projection, wantCL=False)
        cpu_results = cpu_bathy(maxdepth)
        btime2 = time()
        bdelta = btime2-btime1
        print '... finished in ', bdelta, 'seconds!'

        # Compare the results.
        allowed_error_percentage = 1
        maxnomatch = int(allowed_error_percentage*0.01*lenbase)
        xlen, ylen = gpu_results.shape
        if image:
            print 'Generating image of differences'
            import Image, re
            imagefile = re.sub('pkl.gz', 'png', fileobj.name)
            # diffarr = (cpu_results + 128 - gpu_results)
            diffarr = np.array([[int(128 + cpu_results[x,y] - gpu_results[x,y]) for y in xrange(ylen)] for x in xrange(xlen)], dtype=np.int32)
            Image.fromarray(diffarr).save(imagefile)
        else:
            nomatch = sum([1 if abs(cpu_results[x,y] - gpu_results[x,y]) > 0.0001 else 0 for x, y in product(xrange(xlen), xrange(ylen))])
            if nomatch > maxnomatch:
                countprint = 0
                for x, y in product(xrange(xlen), xrange(ylen)):
                    if abs(cpu_results[x,y] - gpu_results[x,y]) > 0.0001:
                        countprint += 1
                        if countprint < 10:
                            print "no match at ", x, y
                            print " CPU: ", cpu_results[x,y]
                            print " GPU: ", gpu_results[x,y]
                        else:
                            break
                raise AssertionError, '%d of %d (%d%%) failed to match' % (nomatch, lenbase, 100*nomatch/lenbase)
            else:
                print '%d of %d (%d%%) failed to match' % (nomatch, lenbase, 100*nomatch/lenbase)
        
if __name__ == '__main__':
    import argparse
    import glob

    parser = argparse.ArgumentParser(description='Test bathy functionality with OpenCL and GDAL.')
    parser.add_argument('files', type=argparse.FileType('r'), nargs='*',
                        help='a data file to be processed')
    parser.add_argument('--image', action='store_true',
                        help='generate an image with the differences')

    args = parser.parse_args()
    if (args.files == []):
        args.files = [open(file) for file in glob.glob('./bathy-*.pkl.gz')]
    for testfile in args.files:
        print 'Testing %s' % testfile.name
        bathy.test(testfile, image=args.image)
        testfile.close()
