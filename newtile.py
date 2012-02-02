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
from newutils import cleanmkdir, ds, setspawnandsave, materialNamed
from timer import timer
from memoize import memoize

import sys
sys.path.append('..')
from pymclevel import mclevel, box
from newtree import Tree, treeObjs

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
        lcarray = mapds.GetRasterBand(Region.rasters['landcover']).ReadAsArray(ox, oy, sx, sy)
        elarray = mapds.GetRasterBand(Region.rasters['elevation']).ReadAsArray(ox, oy, sx, sy)
        bathyarray = mapds.GetRasterBand(Region.rasters['bathy']).ReadAsArray(ox, oy, sx, sy)
        crustarray = mapds.GetRasterBand(Region.rasters['crust']).ReadAsArray(ox, oy, sx, sy)

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
        self.treeobjs = dict([(tree.name, tree) for tree in treeObjs])
        self.trees = dict([(name, list()) for name in self.treeobjs])

        for myx, myz in product(xrange(self.size), xrange(self.size)):
            mcx = int(mcoffsetx+myx)
            mcz = int(mcoffsetz+myz)
            mcy = int(elarray[myz, myx])
            lcval = int(lcarray[myz, myx])
            bathyval = int(bathyarray[myz, myx])
            crustval = int(crustarray[myz, myx])
            if mcy > self.peak[1]:
                self.peak = [mcx, mcy, mcz]
            (blocks, datas, tree) = myterrain.place(mcx, mcy, mcz, lcval, crustval, bathyval)
            [ self.world.setBlockAt(mcx, y, mcz, materialNamed(block)) for (y, block) in blocks if block != 'Air' ]
            [ self.world.setBlockDataAt(mcx, y, mcz, data) for (y, data) in datas if data != 0 ]
            # if trees are placed, elevation cannot be changed
            if tree:
                coords = [mcx, mcy, mcz]
                if (myx < Tree.treeWidth+1 or (self.size-myx) < Tree.treeWidth+1 or
                    myz < Tree.treeWidth+1 or (self.size-myz) < Tree.treeWidth+1):
                    # tree is too close to the edge, plant it later
                    try:
                        self.trees[tree]
                    except KeyError:
                        self.trees[tree] = []
                    self.trees[tree].append(coords)
                else:
                    # plant it now!
                    (blocks, datas) = self.treeobjs[tree](coords)
                    [ self.world.setBlockAt(x, y, z, materialNamed(block)) for (x, y, z, block) in blocks if block != 'Air' ]
                    [ self.world.setBlockDataAt(x, y, z, data) for (x, y, z, data) in datas if data != 0 ]
        # stick the player and the spawn at the peak
        setspawnandsave(self.world, self.peak)

        # write Tile.yaml with relevant data (peak at least)
        # NB: world is not dump-friendly. :-)
        del self.world
        # neither is treeobjs!
        del self.treeobjs
        stream = file(os.path.join(self.tiledir, 'Tile.yaml'), 'w')
        yaml.dump(self, stream)
        stream.close()

        # return peak
        return self.peak

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

