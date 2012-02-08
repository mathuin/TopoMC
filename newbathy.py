# new bathy

from numpy import zeros, uint8
from itertools import product
from math import hypot
from invdisttree import Invdisttree
from timer import timer
from osgeo import gdal

@timer()
def getBathy(deptharray, maxdepth, geotrans, projection):
    # save deptharray as a dataset named depthds
    (depthz, depthx) = deptharray.shape
    drv = gdal.GetDriverByName('MEM')
    depthds = drv.Create('', depthx, depthz, 1, gdal.GetDataTypeByName('Byte'))
    depthds.SetGeoTransform(geotrans)
    depthds.SetProjection(projection)
    depthband = depthds.GetRasterBand(1)
    depthband.WriteArray(deptharray)
    # create a duplicate dataset called bathyds
    bathyds = drv.Create('', depthx, depthz, 1, gdal.GetDataTypeByName('Byte'))
    bathyds.SetGeoTransform(geotrans)
    bathyds.SetProjection(projection)
    bathyband = bathyds.GetRasterBand(1)
    # run compute proximity
    values = ','.join([str(x) for x in xrange(256) if x is not 11])
    options = ['MAXDIST=%d' % maxdepth, 'NODATA=%d' % maxdepth, 'VALUES=%s' % values]
    gdal.ComputeProximity(depthband, bathyband, options)
    # extract array
    bathyarray = bathyband.ReadAsArray(maxdepth, maxdepth, bathyds.RasterXSize-2*maxdepth, bathyds.RasterYSize-2*maxdepth)
    bathyds = None
    depthds = None
    return bathyarray
    
    
