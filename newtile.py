#!/usr/bin/env python

# tile class

from __future__ import division
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from newregion import Region
import os
from itertools import product
import numpy

import newcoords
import invdisttree
#import newterrain
from newutils import cleanmkdir, ds, setspawnandsave
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

    def __init__(self, region, tilex, tiley):
        """Create a tile based on the region and the tile's coordinates."""
        # NB: smart people check that files have been gotten.
        # today we assume that's already been done.
        # snag stuff from the region first
        self.name = region.name
        self.size = region.tilesize
        self.scale = region.scale
        self.lcfile = region.mapfile(region.lclayer)
        self.elfile = region.mapfile(region.ellayer)
        self.tilex = tilex
        self.tiley = tiley
        self.offsetx = self.tilex * self.size
        self.offsety = self.tiley * self.size

        if (self.tilex < region.txmin) or (self.tilex >= region.txmax):
            raise AttributeError, "tilex (%d) must be between %d and %d" % (self.tilex, region.txmin, region.txmax)
        if (self.tiley < region.tymin) or (self.tiley >= region.tymax):
            raise AttributeError, "tiley (%d) must be between %d and %d" % (self.tiley, region.tymin, region.tymax)

    @timer()
    def build(self):
        """Actually build the Minecraft world that corresponds to a tile."""
        # create the tile directory if necessary
        self.tiledir = os.path.join('Tiles', self.name, '%dx%d' % (self.tilex, self.tiley))
        cleanmkdir(self.tiledir)

        # build a Minecraft world via pymclevel from blocks and data
        self.world = mclevel.MCInfdevOldLevel(self.tiledir, create=True)
        tilebox = box.BoundingBox((self.offsetx, 0, self.offsety), (self.size, Tile.chunkHeight, self.size))
        self.world.createChunksInBox(tilebox)

        # build inverse distance trees for landcover and elevation
        # FIXME: we currently read in the entire world
        lcds = ds(self.lcfile)
        elds = ds(self.elfile)
        # landcover nodata is 11
        lcidt = Tile.getIDT(lcds, nodata=11)
        # FIXME: need 'vscale=SOMETHINGSANE' here
        elidt = Tile.getIDT(elds, vscale=self.scale)
        
        # fun with coordinates
        #print "upper left:", newcoords.fromRastertoMap(lcds, 0, 0)
        #print "lower left:",  newcoords.fromRastertoMap(lcds, 0, lcds.RasterYSize)
        #print "upper right:", newcoords.fromRastertoMap(lcds, lcds.RasterXSize, 0)
        #print "lower right:", newcoords.fromRastertoMap(lcds, lcds.RasterXSize, lcds.RasterYSize)

        # the base array
        # the offsets are Minecraft units
        # the size is tilesize
        # the contents are latlongs
        baseshape = (self.size, self.size)
        basearray = newcoords.getCoordsArray(lcds, self.offsetx, self.offsety, self.size, self.size, self.fromMCtoLL)

        # generate landcover and elevation arrays
        lcarray = lcidt(basearray, nnear=8, eps=0.1, majority=True)
        lcarray.resize(baseshape)
        
        elarray = elidt(basearray, nnear=8, eps=0.1)
        elarray.resize(baseshape)
        
        # bathymetry and crust go here 

        # do the terrain thing (no trees, ore or building)
        self.peak = [0, 0, 0]

        for myx, myz in product(xrange(self.size), xrange(self.size)):
            lcval = int(lcarray[myx, myz])
            elval = int(elarray[myx, myz])
            bathyval = 3 # FIXME
            crustval = 5 # FIXME
            realx = myx + self.offsetx
            realz = myz + self.offsety
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
        setspawnandsave(self.world, self.peak)

        # write Tile.yaml with relevant data (peak at least)
        # NB: world is not dump-friendly. :-)
        del self.world
        stream = file(os.path.join(self.tiledir, 'Tile.yaml'), 'w')
        yaml.dump(self, stream)
        stream.close()

        # return peak
        return self.peak
    
    # duplicates region.ds
    @staticmethod
    def ds(name, layer):
        filename = os.path.join('Datasets', name, layer, '%s.%s' % (layer, Region.decodeLayerID(layer)[1]))
        ds = gdal.Open(filename, GA_ReadOnly)
        ds.transforms = newcoords.getTransforms(ds)
        return ds

    @staticmethod
    @timer()
    def getIDT(ds, nodata=None, vscale=1, trim=0):
        """Get inverse distance tree based on dataset."""
        band = ds.GetRasterBand(1)
        # try grabbing only the coordinates we care about
        offset = (0, 0)
        size = (ds.RasterXSize, ds.RasterYSize)
        data = band.ReadAsArray(offset[0], offset[1], size[0], size[1])
        if (nodata != None):
            fromnodata = band.GetNoDataValue()
            data[data == fromnodata] = nodata
        latlong = newcoords.getCoordsArray(ds, offset[0], offset[1], size[0], size[1], newcoords.fromRastertoLL)
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

    # these are Tile-based coords functions because they use self.scale
    def fromMCtoMap(self, ds, MCx, MCz):
        """Used with getCoordsArray to transform from Minecraft units to map units."""
        #     north  south  east  west
        # alb  y+     y-     x+    x-
        #  MC  z-     z+     x+    x-
        mapx = MCx * self.scale
        mapy = MCz * self.scale * -1
        return mapx, mapy

    def fromMCtoLL(self, ds, MCx, MCz):
        mapx, mapy = self.fromMCtoMap(ds, MCx, MCz)
        pnt1, pnt0 = newcoords.fromMaptoLL(ds, mapx, mapy)
        return pnt1, pnt0

    def fromMCtoRaster(self, ds, MCx, MCz):
        mapx, mapy = self.fromMCtoMap(ds, MCx, MCz)
        x, y = newcoords.fromMaptoRaster(ds, mapx, mapy)
        return round(x), round(y)

    def fromMaptoMC(self, ds, mapx, mapy):
        MCx = mapx / self.scale
        MCz = -1 * mapy / self.scale
        return MCx, MCz

    def fromRastertoMC(self, ds, x, y):
        mapx, mapy = newcoords.fromRastertoMap(ds, x, y)
        MCx, MCz = self.fromMaptoMC(ds, mapx, mapy)
        return MCx, MCz

    def fromLLtoMC(self, ds, lat, lon):
        mapx, mapy = newcoords.fromLLtoMap(ds, lat, lon)
        MCx, MCz = self.fromMaptoMC(ds, mapx, mapy)

def checkTile():
    """Checks tile code."""

    # assume newregion.py passed its checks
    yamlfile = file(os.path.join('Regions', 'BI30', 'Region.yaml'))
    Test = yaml.load(yamlfile)
    yamlfile.close()

    try:
        myTile = Tile(Test, Test.txmin-1, Test.tymin-1)
    except AttributeError:
        print "out of bounds tile check passed"
    else:
        print "out of bounds tile check failed"

    # create the tile
    myTile = Tile(Test, Test.txmin, Test.tymin)

    # build the world corresponding to the tile
    myTile.build()

if __name__ == '__main__':
    checkTile()

