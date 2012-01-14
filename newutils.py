# utils module
import os
import shutil
from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly
import newcoords

def cleanmkdir(dir):
    """Cleans out existing directory and rebuilds."""
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    if not os.path.exists(dir):
        os.makedirs(dir)
    else:
        raise IOError, '%s already exists' % dir
    return dir

def ds(filename):
    """Return dataset including transforms."""
    ds = gdal.Open(filename, GA_ReadOnly)
    ds.transforms = newcoords.getTransforms(ds)
    return ds

