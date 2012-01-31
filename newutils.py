# utils module
import os
import shutil
from osgeo import gdal, osr
from osgeo.gdalconst import GA_ReadOnly

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

    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Trans = osr.CoordinateTransformation(Proj, LatLong)
    ArcTrans = osr.CoordinateTransformation(LatLong, Proj)
    GeoTrans = ds.GetGeoTransform()

    ds.transforms = (Trans, ArcTrans, GeoTrans)
    ds.geotrans = ds.GetGeoTransform()
    return ds

def setspawnandsave(world, point):
    """Sets the spawn point and player point in the world and saves the world."""
    world.setPlayerPosition(tuple(point))
    spawn = point
    spawn[1] += 2
    world.setPlayerSpawnPosition(tuple(spawn))
    sizeOnDisk = 0
    # NB: numchunks is calculable = (region.tilesize/chunkWidth)*(region.tilesize/chunkWidth)
    numchunks = 0
    for i, cPos in enumerate(world.allChunks, 1):
        ch = world.getChunk(*cPos);
        numchunks += 1
        sizeOnDisk += ch.compressedSize();
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()
    
