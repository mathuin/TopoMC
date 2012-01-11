# tile class

# REALLY NEED TO SEPARATE OUT THAT WSDL CRAZINESS INTO ANOTHER CLASS

# ./BuildRegion.py does all of this, then generates one big world from all the littles
# in the Tiles/XxY directories and stores it in Region/<name>/World, setting spawn to 
# the first highest altitude plus two Y.

from __future__ import division
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import invdisttree
import coords
from osgeo import gdal, osr
from osgeo.gdalconst import GA_ReadOnly
from newregion import Region
import os
import shutil

# tile.py getIDT
def getIDT(ds, offset, size, vScale=1, nodata=None, trim=0):
    "Convert a portion of a given dataset (identified by corners) to an inverse distance tree."
    # retrieve data from dataset
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])

    # set nodata if it exists
    if (nodata != None):
        fromnodata = Band.GetNoDataValue()
        Data[Data == fromnodata] = nodata
    Band = None

    # build initial arrays
    LatLong = coords.getLatLongArray(ds, (offset), (size), 1)
    Value = Data.flatten()

    # trim elevation
    Value = Value - trim

    # scale elevation vertically
    Value = Value / vScale

    # build tree
    IDT = invdisttree.Invdisttree(LatLong, Value)

    return IDT

# tile.py getOffsetSize
def getOffsetSize(ds, corners, mult=1):
    "Convert corners to offset and size."
    (ul, lr) = corners
    ox, oy = coords.getCoords(ds, ul[0], ul[1])
    print "ox, oy are %f, %f" % (ox, oy)
    offset_x = max(ox, 0)
    offset_y = max(oy, 0)
    fcx, fcy = coords.getCoords(ds, lr[0], lr[1])
    print "fcx, fcy are %f, %f" % (fcx, fcy)
    farcorner_x = min(fcx, ds.RasterXSize)
    farcorner_y = min(fcy, ds.RasterYSize)
    offset = (int(offset_x*mult), int(offset_y*mult))
    size = (int(farcorner_x*mult-offset_x*mult), int(farcorner_y*mult-offset_y*mult))
    print "offset is %d, %d, size is %d, %d" % (offset[0], offset[1], size[0], size[1])
    return offset, size

# tile.py getImageArray
def getImageArrayold(ds, idtCorners, baseArray, vScale=1, nodata=None, majority=False, trim=0):
    "Given the relevant information, builds the image array."
    Offset, Size = getOffsetSize(ds, idtCorners)
    IDT = getIDT(ds, Offset, Size, vScale, nodata, trim)
    ImageArray = IDT(baseArray, nnear=8, eps=0.1, majority=majority)

    return ImageArray

def getImageArray(ds, offset, size, baseArray, vScale=1, nodata=None, majority=False, trim=0):
    "Given the relevant information, builds the image array."
    IDT = getIDT(ds, offset, size, vScale, nodata, trim)
    ImageArray = IDT(baseArray, nnear=8, eps=0.1, majority=majority)

    return ImageArray

class Tile:
    """Tiles are the base render object.  or something."""
    def __init__(self, region, tilex, tiley):
        """Create a tile based on the region and the tile's coordinates."""
        # NB: smart people check that files have been gotten.
        # today we assume that's already been done.

        if (tilex < region.txmin) or (tilex >= region.txmax):
            raise AttributeError, "tilex (%d) must be between %d and %d" % (tilex, region.txmin, region.txmax)
        if (tiley < region.tymin) or (tiley >= region.tymax):
            raise AttributeError, "tiley (%d) must be between %d and %d" % (tiley, region.tymin, region.tymax)

        realsize = region.tilesize * region.scale
        # set offsets
        # effectively negates tile.py:getTileOffsetSize
        self.offsetx = realsize * (tilex - region.txmin)
        self.offsety = realsize * (tiley - region.tymin)

        # create the tile directory if necessary
        tiledir = os.path.join('Regions', region.name, 'Tiles', '%dx%d' % (tilex, tiley))
        self.worlddir = os.path.join(tiledir, 'World')
        if os.path.isdir(tiledir):
            shutil.rmtree(tiledir)
        if not os.path.exists(tiledir):
            os.makedirs(self.worlddir)
        else:
            raise IOError, '%s already exists' % tilesdir

        # generate two mapsize*mapsize arrays for landcover and elevation
        lcimage = region.lcfile()
        lcds = gdal.Open(lcimage, GA_ReadOnly)
        lcds.transforms = coords.getTransforms(lcds)
        lcUL = coords.getLatLong(lcds, self.offsetx - realsize, self.offsety - realsize)
        print lcUL
        lcLR = coords.getLatLong(lcds, self.offsetx + 2 * realsize, self.offsety + 2 * realsize)
        print lcLR
        lccorners = [lcUL, lcLR]
        lcoffset, lcsize = getOffsetSize(lcds, lccorners)
        print lcoffset, lcsize
        # IGNORE baseoffset
        baseoffset = [self.offsetx, self.offsety]
        basesize = [realsize, realsize]
        basecorners = [[self.offsetx, self.offsety], [self.offsetx+realsize, self.offsety+realsize]]
        basearray = coords.getCoordsArray(lcds, baseoffset, basesize)
        

#        lcoffset = [self.offsetx - region.maxdepth, self.offsety - region.maxdepth]
#        lcsize = [mapsize, mapsize]
        lcarray = getImageArray(lcds, lcoffset, lcsize, basearray, nodata=11, majority=True)
        
        # generate one tilesize*tilesize array for bathymetry

        # generate one tilesize*tilesize array for crust values

        # generate two tilesize*height*tilesize arrays for blocks and data

        # do the terrain thing (no trees, ore or building)

        # write Tile.yaml with relevant data (peak at least)

        # build a Minecraft world via pymclevel from blocks and data

        # write that world to the Tiles/XxY/World directory
        raise AttributeError



def checkTile():
    """Checks tile code."""

    #BlockIsland = Region(name='BlockIsland', ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332)
    # assume newregion.py passed its checks
    yamlfile = file(os.path.join('Regions', 'BlockIsland', 'Region.yaml'))
    BlockIsland = yaml.load(yamlfile)
    yamlfile.close()

    try:
        myTile = Tile(BlockIsland, BlockIsland.txmin-1, BlockIsland.tymin-1)
    except AttributeError:
        print "out of bounds tile check passed"
    else:
        print "out of bounds tile check failed"

    myTile = Tile(BlockIsland, BlockIsland.txmin, BlockIsland.tymin)

if __name__ == '__main__':
    checkTile()
