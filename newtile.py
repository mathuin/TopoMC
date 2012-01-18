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
        self.mcsize = region.tilesize
        self.scale = region.scale
        self.mapsize = region.tilesize * region.scale
        self.lcfile = region.mapfile(region.lclayer)
        self.elfile = region.mapfile(region.ellayer)
        self.tilex = int(tilex)
        self.tiley = int(tiley)
        self.mapoffsetx = self.tilex * self.mapsize
        self.mapoffsety = self.tiley * self.mapsize

        if (self.tilex < region.txmin) or (self.tilex >= region.txmax):
            raise AttributeError, "tilex (%d) must be between %d and %d" % (self.tilex, region.txmin, region.txmax)
        if (self.tiley < region.tymin) or (self.tiley >= region.tymax):
            raise AttributeError, "tiley (%d) must be between %d and %d" % (self.tiley, region.tymin, region.tymax)

        # testing MC->Map transformations
        # okay, here's what we've learned.
        # map coords    lat longs    mc coords
        #  X+   Y=      LA-  LO++     X+  Z=   (goes east!)
        #  X=   Y+      LA++ LO+      X=  Z-   (goes north!)
        # so now figure out which value goes north-south and which goes east-west
        # but this is crazy.
        # if True use test transformations
        self.rotate = True
        # if True, exchange X and Y/Z
        self.exchange = True
        # if True, negate the indicated value
        # NB: this takes place *after* exchange
        self.negatefirst = True
        self.negatelast = True

    @timer()
    def build(self):
        """Actually build the Minecraft world that corresponds to a tile."""
        # create the tile directory if necessary
        self.tiledir = os.path.join('Tiles', self.name, '%dx%d' % (self.tilex, self.tiley))
        cleanmkdir(self.tiledir)

        # build inverse distance trees for landcover and elevation
        # FIXME: we currently read in the entire world
        lcds = ds(self.lcfile)
        elds = ds(self.elfile)
        # landcover nodata is 11
        lcidt = self.getIDT(lcds, nodata=11)
        # FIXME: need 'vscale=SOMETHINGSANE' here
        elidt = self.getIDT(elds, vscale=self.scale)

        # calculate Minecraft corners
        mcoffset = self.fromMaptoMC(lcds, self.mapoffsetx, self.mapoffsety)
        mcfar = self.fromMaptoMC(lcds, self.mapoffsetx+self.mapsize, self.mapoffsety+self.mapsize)
        mcoffsetx = min(mcoffset[0], mcfar[0])
        mcoffsetz = min(mcoffset[1], mcfar[1])
        mcfarx = max(mcoffset[0], mcfar[0])
        mcfarz = max(mcoffset[1], mcfar[1])
        mcsizex = mcfarx - mcoffsetx
        mcsizez = mcfarz - mcoffsetz
        if mcsizex < 0 or mcsizez < 0:
            raise AttributeError, 'negative sizes are bad'
        
        # build a Minecraft world via pymclevel from blocks and data
        self.world = mclevel.MCInfdevOldLevel(self.tiledir, create=True)
        tilebox = box.BoundingBox((mcoffsetx, 0, mcoffsetz), (mcsizex, Tile.chunkHeight, mcsizez))
        self.world.createChunksInBox(tilebox)

        # fun with coordinates
        #print "upper left:", newcoords.fromRastertoMap(lcds, 0, 0)
        #print "lower left:",  newcoords.fromRastertoMap(lcds, 0, lcds.RasterYSize)
        #print "upper right:", newcoords.fromRastertoMap(lcds, lcds.RasterXSize, 0)
        #print "lower right:", newcoords.fromRastertoMap(lcds, lcds.RasterXSize, lcds.RasterYSize)

        # the base array
        # the offsets are map units
        # the size is tilesize
        # the contents are latlongs
        llshape = (self.mcsize, self.mcsize)
        llarray = newcoords.getCoordsArray(lcds, self.tilex*self.mcsize, self.tiley*self.mcsize, self.mcsize, self.mcsize, newcoords.fromMaptoLL, self.scale)

        # the Minecraft coordinate translation
        # NB: very suspicious values coming from this sigh!
        mcarray = newcoords.getCoordsArray(lcds, self.tilex*self.mcsize, self.tiley*self.mcsize, self.mcsize, self.mcsize, self.fromMaptoMC, self.scale)

        # generate landcover and elevation arrays
        lcarray = lcidt(llarray, nnear=8, eps=0.1, majority=True)
        lcarray.resize(llshape)
        
        elarray = elidt(llarray, nnear=8, eps=0.1)
        elarray.resize(llshape)
        
        # bathymetry and crust go here 

        # do the terrain thing (no trees, ore or building)
        self.peak = [0, 0, 0]

        for myx, myz in product(xrange(self.mcsize), xrange(self.mcsize)):
            if False:
                mcindex = myx+self.mcsize*myz
                mcx = mcarray[mcindex][0]
                mcz = mcarray[mcindex][1]
            else:
                mcx = myx + mcoffsetx
                mcz = myz + mcoffsetz
            lcval = int(lcarray[myx, myz])
            elval = int(elarray[myx, myz])
            bathyval = 3 # FIXME
            crustval = 5 # FIXME
            mcel = elval + Tile.sealevel
            if elval > self.peak[1]:
                self.peak = [mcx, mcel, mcz]
            #processTerrain(lcval, myx, myz, elval, bathyval, crustval)
            # FIXME: for now, dirt or no dirt, to the appropriate altitude
            if (lcval == 11):
                columns = [crustval, self.world.materials.Sand.ID, bathyval, self.world.materials.Water.ID]
            else:
                columns = [crustval, self.world.materials.Dirt.ID]
            self.templayers(mcx, mcz, mcel, columns)
            
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
    def getIDT(self, ds, nodata=None, vscale=1, trim=0, all=False):
        """Get inverse distance tree based on dataset."""
        offset = newcoords.fromMaptoRaster(ds, self.mapoffsetx-self.mapsize, self.mapoffsety-self.mapsize)
        far = newcoords.fromMaptoRaster(ds, self.mapoffsetx+self.mapsize*2, self.mapoffsety+self.mapsize*2)
        ox = int(max(0, min(offset[0], far[0])))
        oy = int(max(0, min(offset[1], far[1])))
        fx = int(min(ds.RasterXSize, max(offset[0], far[0])))
        fy = int(min(ds.RasterYSize, max(offset[1], far[1])))
        sx = fx - ox
        sy = fy - oy
        if all==True:
            print "o = (%d, %d), f = (%d, %d), s = (%s, %s)" % (ox, oy, fx, fy, sx, sy)
            print "was (0, 0, %d, %d) now is (%d, %d, %d, %d)" % (ds.RasterXSize, ds.RasterYSize, ox, oy, sx, sy)
            print " - would have loaded only %d percent!" % (100 * (sx * sy) / (ds.RasterXSize * ds.RasterYSize))
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
        top = elval
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
        if self.rotate == True:
            if self.exchange == True:
                mapx = MCz * self.scale
                mapy = MCx * self.scale
            else:
                mapx = MCx * self.scale
                mapy = MCz * self.scale
            if self.negatefirst == True:
                mapx = -1 * mapx
            if self.negatelast == True:
                mapy = -1 * mapy
        else:
            mapx = MCx * self.scale
            mapy = MCz * self.scale
        return round(mapx), round(mapy)

    def fromMCtoLL(self, ds, MCx, MCz):
        mapx, mapy = self.fromMCtoMap(ds, MCx, MCz)
        pnt1, pnt0 = newcoords.fromMaptoLL(ds, mapx, mapy)
        return pnt1, pnt0

    def fromMCtoRaster(self, ds, MCx, MCz):
        mapx, mapy = self.fromMCtoMap(ds, MCx, MCz)
        x, y = newcoords.fromMaptoRaster(ds, mapx, mapy)
        return x, y

    def fromMaptoMC(self, ds, mapx, mapy):
        if self.rotate == True:
            if self.exchange == True:
                MCx = mapy / self.scale
                MCz = mapx / self.scale
            else:
                MCx = mapx / self.scale
                MCz = mapy / self.scale
            # negate ones are backwards for obvious reasons
            if self.negatefirst == True:
                MCz = -1 * MCz
            if self.negatelast == True:
                MCx = -1 * MCx
        else:
            MCx = mapx / self.scale
            MCz = mapy / self.scale
        return round(MCx), round(MCz)

    def fromRastertoMC(self, ds, x, y):
        mapx, mapy = newcoords.fromRastertoMap(ds, x, y)
        MCx, MCz = self.fromMaptoMC(ds, mapx, mapy)
        return MCx, MCz

    def fromLLtoMC(self, ds, lat, lon):
        mapx, mapy = newcoords.fromLLtoMap(ds, lat, lon)
        MCx, MCz = self.fromMaptoMC(ds, mapx, mapy)
        return MCx, MCz

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

