#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
from tile import Tile
from utils import setspawnandsave
import argparse
import os
import yaml
from multiprocessing import Pool
from itertools import product
from tree import Tree, treeObjs
from ore import Ore, oreObjs
from pymclevel import mclevel

def buildtile(args):
    """Given a region name and coordinates, build the corresponding tile."""
    # this should work for single and multi threaded cases
    (name, tilex, tiley) = args
    yamlfile = file(os.path.join('Regions', name, 'Region.yaml'))
    myRegion = yaml.load(yamlfile)
    yamlfile.close()
    myTile = Tile(myRegion, tilex, tiley)
    myTile()

def main():
    """Builds a region."""
    # example:
    # ./BuildRegion.py --name BlockIsland

    # parse options and get results
    parser = argparse.ArgumentParser(description='Builds Minecraft worlds from regions.')
    parser.add_argument('--name', required=True, type=str, help='name of the region to be built')
    parser.add_argument('--debug', action='store_true', help='enable debug output')
    parser.add_argument('--single', action='store_true', help='enable single-threaded mode for debugging or profiling')
    args = parser.parse_args()

    # enable debug
    if (args.debug):
        print "Do something!"

    # build the region
    print "Building region %s..." % args.name
    yamlfile = file(os.path.join('Regions', args.name, 'Region.yaml'))
    myRegion = yaml.load(yamlfile)
    yamlfile.close()

    # exit if map does not exist
    if not os.path.exists(myRegion.mapfile):
        raise IOError, "no map file exists"

    # tree and ore variables
    treeobjs = dict([(tree.name, tree) for tree in treeObjs])
    trees = dict([(name, list()) for name in treeobjs])
    oreobjs = dict([(ore.name, ore) for ore in oreObjs])
    ores = dict([(name, list()) for name in oreobjs])

    # generate overall world
    worlddir = os.path.join('Worlds', args.name)
    world = mclevel.MCInfdevOldLevel(worlddir, create=True)
    peak = [0, 0, 0]

    # generate individual tiles
    tilexrange = xrange(myRegion.tiles['xmin'], myRegion.tiles['xmax'])
    tileyrange = xrange(myRegion.tiles['ymin'], myRegion.tiles['ymax'])
    name = myRegion.name
    tiles = [(name, x, y) for x, y in product(tilexrange, tileyrange)]
    if args.single:
        # single process version - works
        for tile in tiles:
            buildtile(tile)
    else:
        # multi-process ... let's see...
        pool = Pool()
        pool.map(buildtile, tiles)
        pool.close()
        pool.join()

    # merge individual worlds into it
    print "Merging %d tiles into one world..." % len(tiles)
    for tile in tiles:
        (name, x, y) = tile
        tiledir = os.path.join('Regions', name, 'Tiles', '%dx%d' % (x, y))
        tilefile = file(os.path.join(tiledir, 'Tile.yaml'))
        newtile = yaml.load(tilefile)
        tilefile.close()
        if (newtile.peak[1] > peak[1]):
            peak = newtile.peak
        for treetype in newtile.trees:
            trees.setdefault(treetype, []).extend(newtile.trees[treetype])
        if myRegion.doOre:
            for oretype in newtile.ores:
                ores.setdefault(oretype, []).extend(newtile.ores[oretype])
        tileworld = mclevel.MCInfdevOldLevel(tiledir, create=False)
        world.copyBlocksFrom(tileworld, tileworld.bounds, tileworld.bounds.origin)
        tileworld = False

    # plant trees in our world
    print "Planting %d trees at the region level..." % sum([len(trees[treetype]) for treetype in trees])
    Tree.placetreesinregion(trees, treeobjs, world)

    # deposit ores in our world
    if myRegion.doOre:
        print "Depositing %d ores at the region level..." % sum([len(ores[oretype]) for oretype in ores])
        Ore.placeoreinregion(ores, oreobjs, world)

    # replace all 'end stone' with stone
    print "Replacing all 'end stone' with stone..."
    EndStoneID = world.materials["End Stone"].ID
    StoneID = world.materials["Stone"].ID
    for xpos, zpos in world.allChunks:
        chunk = world.getChunk(xpos, zpos)
        chunk.Blocks[chunk.Blocks == EndStoneID] = StoneID

    # tie up loose ends
    setspawnandsave(world, peak)

if __name__ == '__main__':
    main()

