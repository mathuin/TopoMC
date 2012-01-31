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

from newl01 import L01_Terrain
from newutils import cleanmkdir, ds, setspawnandsave
from timer import timer
from memoize import memoize

import sys
sys.path.append('..')
from pymclevel import mclevel, box
from pymclevel.materials import alphaMaterials

class Tile:
    """Tiles are the base render object.  or something."""

    # stuff that should come from pymclevel    
    crustwidth = 3

    def __init__(self, region, tilex, tiley):
        """Create a tile based on the region and the tile's coordinates."""
        # NB: smart people check that files have been gotten.
        # today we assume that's already been done.
        # snag stuff from the region first
        self.name = region.name
        self.size = region.tilesize
        self.mapname = region.mapname
        self.tilex = int(tilex)
        self.tiley = int(tiley)
        self.tiles = region.tiles
        self.rasters = region.rasters

        if (self.tilex < self.tiles['xmin']) or (self.tilex >= self.tiles['xmax']):
            raise AttributeError, "tilex (%d) must be between %d and %d" % (self.tilex, self.tiles['xmin'], self.tiles['xmax'])
        if (self.tiley < self.tiles['ymin']) or (self.tiley >= self.tiles['ymax']):
            raise AttributeError, "tiley (%d) must be between %d and %d" % (self.tiley, self.tiles['ymin'], self.tiles['ymax'])

        # create the tile directory if necessary
        self.tiledir = os.path.join(region.regiondir, 'Tiles', '%dx%d' % (self.tilex, self.tiley))
        cleanmkdir(self.tiledir)

    @timer()
    def build(self):
        """Actually build the Minecraft world that corresponds to a tile."""

        # calculate offsets
        ox = (self.tilex-self.tiles['xmin'])*self.size
        oy = (self.tiley-self.tiles['ymin'])*self.size
        sx = self.size
        sy = self.size

        # load arrays from map file
        mapds = ds(self.mapname)
        lcarray = mapds.GetRasterBand(self.rasters['landcover']).ReadAsArray(ox, oy, sx, sy)
        elarray = mapds.GetRasterBand(self.rasters['elevation']).ReadAsArray(ox, oy, sx, sy)
        bathyarray = mapds.GetRasterBand(self.rasters['bathy']).ReadAsArray(ox, oy, sx, sy)
        crustarray = mapds.GetRasterBand(self.rasters['crust']).ReadAsArray(ox, oy, sx, sy)

        # calculate Minecraft corners
        mcoffsetx = self.tilex * self.size
        mcoffsetz = self.tiley * self.size
        
        # build a Minecraft world via pymclevel from blocks and data
        self.world = mclevel.MCInfdevOldLevel(self.tiledir, create=True)
        tilebox = box.BoundingBox((mcoffsetx, 0, mcoffsetz), (self.size, self.world.Height, self.size))
        self.world.createChunksInBox(tilebox)

        # do the terrain thing (no trees, ore or building)
        # FIXME: Region.buildmap() will have to transform from real L01 to "my new class"
        myterrain = L01_Terrain()
        self.peak = [0, 0, 0]

        for myx, myz in product(xrange(self.size), xrange(self.size)):
            mcx = int(mcoffsetx+myx)
            mcz = int(mcoffsetz+myz)
            mcy = int(elarray[myz, myx])
            lcval = int(lcarray[myz, myx])
            bathyval = int(bathyarray[myz, myx])
            crustval = int(crustarray[myz, myx])
            if mcy > self.peak[1]:
                self.peak = [mcx, mcy, mcz]
            columns = myterrain.place(lcval, crustval, bathyval)
            self.templayers(mcx, mcy, mcz, columns)
            
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


    @staticmethod
    @memoize()
    def materialNamed(string):
        "Returns block ID for block with name given in string."
        return [v.ID for v in alphaMaterials.allBlocks if v.name==string][0]

    @staticmethod
    @memoize()
    def names(blockID):
        "Returns block name for given block ID."
        return alphaMaterials.names[blockID][0]

    def templayers(self, x, y, z, column):
        """Attempt to do layers."""
        blocks = []
        top = y
        overstone = sum([column[elem] for elem in xrange(len(column)) if elem % 2 == 0])
        column.insert(0, 'Bedrock')
        column.insert(1, top-overstone-1)
        column.insert(2, 'Stone')
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
        [ self.world.setBlockAt(x, y, z, Tile.materialNamed(block)) for (x, y, z, block) in blocks ]

def checkTile():
    """Checks tile code."""

    # assume newregion.py passed its checks
    yamlfile = file(os.path.join('Regions', 'Test2', 'Region.yaml'))
    Test2 = yaml.load(yamlfile)
    yamlfile.close()

    try:
        myTile = Tile(Test2, Test2.txmin-1, Test2.tymin-1)
    except AttributeError:
        print "out of bounds tile check passed"
    else:
        print "out of bounds tile check failed"

    # create the tile
    myTile = Tile(Test2, Test2.txmin, Test2.tymin)

    # build the world corresponding to the tile
    myTile.build()

if __name__ == '__main__':
    checkTile()

