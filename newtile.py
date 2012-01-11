#!/usr/bin/env python

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

        realsize = region.tilesize * region.mult
        # set offsets
        offsetx = region.tilesize * (tilex - region.txmin + 1)
        offsety = region.tilesize * (tiley - region.tymin + 1)

        # create the tile directory if necessary
        tiledir = os.path.join('Regions', region.name, 'Tiles', '%dx%d' % (tilex, tiley))
        self.worlddir = os.path.join(tiledir, 'World')
        if os.path.isdir(tiledir):
            shutil.rmtree(tiledir)
        if not os.path.exists(tiledir):
            os.makedirs(self.worlddir)
        else:
            raise IOError, '%s already exists' % tilesdir

        # open landcover and elevation datasets
        lcimage = region.lcfile()
        lcds = gdal.Open(lcimage, GA_ReadOnly)
        lcds.transforms = coords.getTransforms(lcds)
        print lcds.RasterXSize
        elimage = region.elfile()
        elds = gdal.Open(elimage, GA_ReadOnly)
        elds.transforms = coords.getTransforms(elds)

        print "hrm!something about / mult here makes sense"

        # generate two mapsize*mapsize arrays for landcover and elevation
        Tile.newgetOffsetSize(lcds, offsetx - region.tilesize, offsetx + 2 * region.tilesize, offsety - region.tilesize, offsety + 2 * region.tilesize)
        
        # generate one tilesize*tilesize array for bathymetry

        # generate one tilesize*tilesize array for crust values

        # generate two tilesize*height*tilesize arrays for blocks and data

        # do the terrain thing (no trees, ore or building)

        # write Tile.yaml with relevant data (peak at least)

        # build a Minecraft world via pymclevel from blocks and data

        # write that world to the Tiles/XxY/World directory
        raise AttributeError

    @staticmethod
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
        LatLong = getLatLongArray(ds, (offset), (size), 1)
        Value = Data.flatten()

        # trim elevation
        Value = Value - trim

        # scale elevation vertically
        Value = Value / vScale

        # build tree
        IDT = invdisttree.Invdisttree(LatLong, Value)

        return IDT

    @staticmethod
    def getOffsetSize(ds, corners, mult=1):
        """Convert lat-long corners to coords offset and size."""
        (ul, lr) = corners
        ox, oy = getCoords(ds, ul[0], ul[1])
        offset_x = max(ox, 0)
        offset_y = max(oy, 0)
        fcx, fcy = getCoords(ds, lr[0], lr[1])
        farcorner_x = min(fcx, ds.RasterXSize)
        farcorner_y = min(fcy, ds.RasterYSize)
        offset = (int(offset_x*mult), int(offset_y*mult))
        size = (int(farcorner_x*mult-offset_x*mult), int(farcorner_y*mult-offset_y*mult))
        #tilelogger.debug("offset is %d, %d, size is %d, %d" % (offset[0], offset[1], size[0], size[1]))
        return offset, size

    @staticmethod
    def newgetOffsetSize(ds, xmin, xmax, ymin, ymax, mult=1):
        ox, oy = coords.getLatLong(ds, xmin, ymax)
        print xmin, ymax, ox, oy
        fcx, fcy = coords.getLatLong(ds, xmax, ymin)
        print xmax, ymin, fcx, fcy
        raise AttributeError

    @staticmethod
    def getImageArray(ds, idtCorners, baseArray, vScale=1, nodata=None, majority=False, trim=0):
        "Given the relevant information, builds the image array."
        Offset, Size = getOffsetSize(ds, idtCorners)
        IDT = getIDT(ds, Offset, Size, vScale, nodata, trim)
        ImageArray = IDT(baseArray, nnear=8, eps=0.1, majority=majority)

        return ImageArray

    @staticmethod
    def getTileOffsetSize(rowIndex, colIndex, tileShape, maxRows, maxCols, idtPad=0):
        "run this with idtPad=0 to generate image."
        imageRows = tileShape[0]
        imageCols = tileShape[1]
        imageLeft = max(rowIndex*imageRows-idtPad, 0)
        imageRight = min(imageLeft+imageRows+2*idtPad, maxRows)
        imageUpper = max(colIndex*imageCols-idtPad, 0)
        imageLower = min(imageUpper+imageCols+2*idtPad, maxCols)
        imageOffset = (imageLeft, imageUpper)
        imageSize = (imageRight-imageLeft, imageLower-imageUpper)
        return imageOffset, imageSize

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
