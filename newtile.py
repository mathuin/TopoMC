#!/usr/bin/env python

# tile class

from __future__ import division
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from osgeo import gdal, osr
from osgeo.gdalconst import GA_ReadOnly
from newregion import Region
import os
import shutil
from itertools import product
import numpy

import newcoords
import invdisttree
#import newterrain
from timer import timer

import sys
sys.path.append('..')
from pymclevel import mclevel, box

class Tile:
    """Tiles are the base render object.  or something."""

    # stuff that should come from pymclevel
    chunkHeight = mclevel.MCInfdevOldLevel.Height # 128 actually
    chunkWidth = 16 # hardcoded in InfdevChunk actually
    sealevel = 32
    maxdepth = 16
    crustwidth = 3

    @timer()
    def __init__(self, region, tilex, tiley):
        """Create a tile based on the region and the tile's coordinates."""
        # NB: smart people check that files have been gotten.
        # today we assume that's already been done.

        if (tilex < region.txmin) or (tilex >= region.txmax):
            raise AttributeError, "tilex (%d) must be between %d and %d" % (tilex, region.txmin, region.txmax)
        if (tiley < region.tymin) or (tiley >= region.tymax):
            raise AttributeError, "tiley (%d) must be between %d and %d" % (tiley, region.tymin, region.tymax)

        # create the tile directory if necessary
        tiledir = os.path.join('Regions', region.name, 'Tiles', '%dx%d' % (tilex, tiley))
        if os.path.isdir(tiledir):
            shutil.rmtree(tiledir)
        if not os.path.exists(tiledir):
            os.makedirs(tiledir)
        else:
            raise IOError, '%s already exists' % tilesdir

        # offsets
        offsetx = tilex * region.tilesize
        offsety = tiley * region.tilesize
        print "yay offsetx is %d and offsety is %d" % (offsetx, offsety)

        # build a Minecraft world via pymclevel from blocks and data
        self.world = mclevel.MCInfdevOldLevel(tiledir, create=True)
        tilebox = box.BoundingBox((offsetx, 0, offsety), (region.tilesize, Tile.chunkHeight, region.tilesize))
        self.world.createChunksInBox(tilebox)

        # build inverse distance trees for landcover and elevation
        # (see if they've been passed to us already)
        try:
            lcds = region.lcds
            elds = region.elds
            lcidt = region.lcidt
            elidt = region.elidt
        except AttributeError:
            # FIXME: we currently read in the entire world
            lcds = region.ds(region.lclayer)
            elds = region.ds(region.ellayer)
            # landcover nodata is 11
            lcidt = Tile.getIDT(lcds, nodata=11)
            # FIXME: need 'vscale=SOMETHINGSANE' here
            elidt = Tile.getIDT(elds, vscale=region.scale)
        
        # fun with coordinates
        #print "upper left:", newcoords.fromRastertoMap(lcds, 0, 0)
        #print "lower left:",  newcoords.fromRastertoMap(lcds, 0, lcds.RasterYSize)
        #print "upper right:", newcoords.fromRastertoMap(lcds, lcds.RasterXSize, 0)
        #print "lower right:", newcoords.fromRastertoMap(lcds, lcds.RasterXSize, lcds.RasterYSize)

        # the base array
        # the offsets are Minecraft units
        # the size is tilesize
        # the contents are latlongs
        baseshape = (region.tilesize, region.tilesize)
        basearray = newcoords.getCoordsArray(lcds, offsetx, offsety, region.tilesize, region.tilesize, newcoords.fromMaptoLL, region.scale)

        # generate landcover and elevation arrays
        lcarray = lcidt(basearray, nnear=8, eps=0.1, majority=True)
        lcarray.resize(baseshape)
        
        elarray = elidt(basearray, nnear=8, eps=0.1)
        elarray.resize(baseshape)
        
        # bathymetry and crust go here 

        # do the terrain thing (no trees, ore or building)
        self.peak = [0, 0, 0]

        for myx, myz in product(xrange(region.tilesize), xrange(region.tilesize)):
            # I FORGET WHY THIS IS Z, X
            lcval = int(lcarray[myz, myx])
            elval = int(elarray[myz, myx])
            bathyval = 3 # FIXME
            crustval = 5 # FIXME
            realx = myx + offsetx
            realz = myz + offsety
            if elval > self.peak[1]:
                self.peak = [realx, elval, realz]
            #processTerrain(lcval, myx, myz, elval, bathyval, crustval)
            # FIXME: for now, dirt or no dirt, to the appropriate altitude
            if (lcval == 11):
                columns = [crustval, self.world.materials.Sand.ID, bathyval, self.world.materials.Water.ID]
            else:
                columns = [crustval, self.world.materials.Dirt.ID]
            self.templayers(realx, realz, elval, columns)
            
        # stick the player and the spawn at the peak
        self.world.setPlayerPosition(tuple(self.peak))
        spawn = self.peak
        spawn[1] += 2
        self.world.setPlayerSpawnPosition(tuple(spawn))
        # write that world to the Tiles/XxY/World directory
        sizeOnDisk = 0
        # NB: numchunks is calculable = (region.tilesize/chunkWidth)*(region.tilesize/chunkWidth)
        numchunks = 0
        for i, cPos in enumerate(self.world.allChunks, 1):
            ch = self.world.getChunk(*cPos);
            numchunks += 1
            sizeOnDisk += ch.compressedSize();
        self.world.SizeOnDisk = sizeOnDisk
        self.world.saveInPlace()

        # write Tile.yaml with relevant data (peak at least)
        # NB: world is not dump-friendly. :-)
        del self.world
        stream = file(os.path.join(tiledir, 'Tile.yaml'), 'w')
        yaml.dump(self, stream)
        stream.close()


    @staticmethod
    @timer()
    def getIDT(ds, nodata=None, vscale=1, trim=0):
        """Get inverse distance tree based on dataset."""
        band = ds.GetRasterBand(1)
        data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
        if (nodata != None):
            fromnodata = band.GetNoDataValue()
            data[data == fromnodata] = nodata
        latlong = newcoords.getCoordsArray(ds, 0, 0, ds.RasterXSize, ds.RasterYSize, newcoords.fromRastertoLL)
        #print latlong
        value = data.flatten()
        value = value - trim
        value = value / vscale
        IDT = invdisttree.Invdisttree(latlong, value)
        return IDT

    def templayers(self, x, z, elval, column):
        """Attempt to do layers."""
        blocks = []
        top = Tile.sealevel+elval
        overstone = sum([column[elem] for elem in xrange(len(column)) if elem % 2 == 0])
        column.insert(0, self.world.materials.Bedrock.ID)
        column.insert(1, top-overstone-1)
        column.insert(2, self.world.materials.Stone.ID)
        while (len(column) > 0 or top > 0):
            # better be a block
            block = column.pop()
            if (len(column) > 0):
                layer = column.pop()
            else:
                layer = top
            # now do something
            if (layer > 0):
                [blocks.append((x, y, z, block)) for y in xrange(top-layer,top)]
                top -= layer
        [ self.world.setBlockAt(x, y, z, block) for (x, y, z, block) in blocks ]

    # NEED TO REIMPLEMENT SETBLOCKSAT AND FRIENDS

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

    # set the inverse distance trees first
    BlockIsland.lcds = BlockIsland.ds(BlockIsland.lclayer)
    BlockIsland.elds = BlockIsland.ds(BlockIsland.ellayer)
    BlockIsland.lcidt = Tile.getIDT(BlockIsland.lcds, nodata=11)
    BlockIsland.elidt = Tile.getIDT(BlockIsland.elds, vscale=BlockIsland.scale)

    myTile = Tile(BlockIsland, 1309, 1485)

if __name__ == '__main__':
    checkTile()

