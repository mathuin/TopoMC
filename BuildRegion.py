#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
from newregion import Region
from newtile import Tile
from newutils import setspawnandsave, materialNamed, names
import sys
import argparse
import os
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from multiprocessing import Pool
from itertools import product
from newtree import Tree, treeObjs
from newore import Ore, oreObjs, oreDQ

sys.path.append('..')
from pymclevel import mclevel, box

def main(argv):
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
    if not os.path.exists(myRegion.mapname):
        raise IOError, "no map file exists"

    # generate overall world
    worlddir = os.path.join('Worlds', args.name)
    world = mclevel.MCInfdevOldLevel(worlddir, create=True)
    peak = [0, 0, 0]

    # generate individual tiles
    # if I ever get this blessed thing to work,
    # use a callback to return the peak
    # AND add the world to the uberworld
    # ... that will save a loop at the least!
    tiles = [(tilex, tiley) for tilex, tiley in product(xrange(myRegion.tiles['xmin'], myRegion.tiles['xmax']), xrange(myRegion.tiles['ymin'], myRegion.tiles['ymax']))]
    if args.single:
        # single process version - works
        for tile in tiles:
            (tilex, tiley) = tile
            myTile = Tile(myRegion, tilex, tiley)
            myTile.build()
    else:
        # multi-process ... let's see...
        pool = Pool()
        tasks = ["./BuildTile.py %s %d %d" % (myRegion.name, tilex, tiley) for (tilex, tiley) in tiles]
        results = pool.map(os.system, tasks)
        peaks = [x for x in results]
        pool = None

    # tree and ore variables
    treeobjs = dict([(tree.name, tree) for tree in treeObjs])
    trees = dict([(name, list()) for name in treeobjs])
    oreobjs = dict([(ore.name, ore) for ore in oreObjs])
    ores = dict([(name, list()) for name in oreobjs])

    # merge individual worlds into it
    print "Merging %d tiles into one world..." % len(tiles)
    for tile in tiles:
        (tilex, tiley) = tile
        tiledir = os.path.join('Regions', myRegion.name, 'Tiles', '%dx%d' % (tilex, tiley))
        tilefile = file(os.path.join(tiledir, 'Tile.yaml'))
        newtile = yaml.load(tilefile)
        tilefile.close()
        if (newtile.peak[1] > peak[1]):
            peak = newtile.peak
        for treetype in newtile.trees:
            coords = newtile.trees[treetype]
            try:
                trees[treetype]
            except KeyError:
                trees[treetype] = []
            trees[treetype] += coords
        if myRegion.doOre:
            for oretype in newtile.ores:
                coords = newtile.ores[oretype]
                try:
                    ores[oretype]
                except KeyError:
                    ores[oretype] = []
                ores[oretype] += coords
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

    # tie up loose ends
    setspawnandsave(world, peak)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

