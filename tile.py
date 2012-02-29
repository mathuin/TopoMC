#!/usr/bin/env python

# tile class

from __future__ import division
import yaml
from region import Region
import os
from itertools import product

from utils import cleanmkdir, setspawnandsave
from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly

import sys
sys.path.append('..')
from pymclevel import mclevel, box
from terrain import Terrain
from tree import Tree, treeObjs
from ore import Ore

class Tile:
    """Tiles are the base render object.  or something."""

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
        self.doOre = region.doOre
        self.doSchematics = region.doSchematics

        if (self.tilex < self.tiles['xmin']) or (self.tilex >= self.tiles['xmax']):
            raise AttributeError, "tilex (%d) must be between %d and %d" % (self.tilex, self.tiles['xmin'], self.tiles['xmax'])
        if (self.tiley < self.tiles['ymin']) or (self.tiley >= self.tiles['ymax']):
            raise AttributeError, "tiley (%d) must be between %d and %d" % (self.tiley, self.tiles['ymin'], self.tiles['ymax'])

        # create the tile directory if necessary
        self.tiledir = os.path.join(region.regiondir, 'Tiles', '%dx%d' % (self.tilex, self.tiley))
        cleanmkdir(self.tiledir)

    def build(self):
        """Actually build the Minecraft world that corresponds to a tile."""

        # calculate offsets
        ox = (self.tilex-self.tiles['xmin'])*self.size
        oy = (self.tiley-self.tiles['ymin'])*self.size
        sx = self.size
        sy = self.size

        # load arrays from map file
        mapds = gdal.Open(self.mapname, GA_ReadOnly)
        lcarray = mapds.GetRasterBand(Region.rasters['landcover']).ReadAsArray(ox, oy, sx, sy)
        elarray = mapds.GetRasterBand(Region.rasters['elevation']).ReadAsArray(ox, oy, sx, sy)
        bathyarray = mapds.GetRasterBand(Region.rasters['bathy']).ReadAsArray(ox, oy, sx, sy)
        crustarray = mapds.GetRasterBand(Region.rasters['crust']).ReadAsArray(ox, oy, sx, sy)

        # calculate Minecraft corners
        self.mcoffsetx = self.tilex * self.size
        self.mcoffsetz = self.tiley * self.size
        
        # build a Minecraft world via pymclevel from blocks and data
        self.world = mclevel.MCInfdevOldLevel(self.tiledir, create=True)
        tilebox = box.BoundingBox((self.mcoffsetx, 0, self.mcoffsetz), (self.size, self.world.Height, self.size))
        self.world.createChunksInBox(tilebox)

        # do the terrain thing (no trees, ore or building)
        self.peak = [0, 0, 0]
        treeobjs = dict([(tree.name, tree) for tree in treeObjs])
        self.trees = dict([(name, list()) for name in treeobjs])

        for myx, myz in product(xrange(self.size), xrange(self.size)):
            mcx = int(self.mcoffsetx+myx)
            mcz = int(self.mcoffsetz+myz)
            mcy = int(elarray[myz, myx])
            lcval = int(lcarray[myz, myx])
            bathyval = int(bathyarray[myz, myx])
            crustval = int(crustarray[myz, myx])
            if mcy > self.peak[1]:
                self.peak = [mcx, mcy, mcz]
            (blocks, datas, tree) = Terrain.place(mcx, mcy, mcz, lcval, crustval, bathyval, self.doSchematics)
            [ self.world.setBlockAt(mcx, y, mcz, block) for (y, block) in blocks if block != 0 ]
            [ self.world.setBlockDataAt(mcx, y, mcz, data) for (y, data) in datas if data != 0 ]
            # if trees are placed, elevation cannot be changed
            if tree:
                Tree.placetreeintile(self, tree, mcx, mcy, mcz)

        # now that terrain and trees are done, place ore
        if self.doOre:
            Ore.placeoreintile(self)

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
