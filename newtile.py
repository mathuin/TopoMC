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
    sealevel = 64
    maxdepth = 32
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
        lcidt = self.getIDT(lcds, nodata=11)
        # FIXME: need 'vscale=SOMETHINGSANE' here
        elidt = self.getIDT(elds, vscale=self.scale)
        
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
            realel = elval + Tile.sealevel
            realz = myz + self.offsety
            if elval > self.peak[1]:
                self.peak = [realx, realel, realz]
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
    
    #@staticmethod due to raster
    @timer()
    def getIDT(self, ds, nodata=None, vscale=1, trim=0):
        """Get inverse distance tree based on dataset."""
        origin = self.fromMCtoRaster(ds, self.offsetx-self.size, self.offsety-self.size)
        print "origin is %d, %d" % (origin[0], origin[1])
        far = self.fromMCtoRaster(ds, self.offsetx+self.size*3, self.offsety+self.size*3)
        print "far is %d, %d" % (far[0], far[1])
        ox = int(max(0, min(origin[0], far[0])))
        oy = int(max(0, min(origin[1], far[1])))
        fx = int(min(ds.RasterXSize, max(origin[0], far[0])))
        fy = int(min(ds.RasterYSize, max(origin[1], far[1])))
        sx = fx - ox
        sy = fy - oy
        print "o = (%d, %d), f = (%d, %d), s = (%s, %s)" % (ox, oy, fx, fy, sx, sy)
	print "was (0, 0, %d, %d) now is (%d, %d, %d, %d)" % (ds.RasterXSize, ds.RasterYSize, ox, oy, sx, sy)
        (ox, oy, sx, sy) = (0, 0, ds.RasterXSize, ds.RasterYSize)
        band = ds.GetRasterBand(1)
        data = band.ReadAsArray(ox, oy, sx, sy)
        if (nodata != None):
            fromnodata = band.GetNoDataValue()
            data[data == fromnodata] = nodata
        latlong = newcoords.getCoordsArray(ds, ox, oy, sx, sy, newcoords.fromRastertoLL, 1)
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
        mapx = MCz * self.scale
        mapy = MCx * self.scale * -1
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
        MCx = -1 * mapy / self.scale
        MCz = mapx / self.scale
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

