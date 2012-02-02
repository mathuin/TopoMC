#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
from newregion import Region
from newtile import Tile
from newutils import setspawnandsave, materialNamed
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
    args = parser.parse_args()

    # enable debug
    if (args.debug):
        print "Do something!"

    # build the region
    print "Building region %s..." % args.name
    yamlfile = file(os.path.join('Regions', args.name, 'Region.yaml'))
    myRegion = yaml.load(yamlfile)
    yamlfile.close()

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
    if False:
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

    # tree variables
    treeobjs = dict([(tree.name, tree) for tree in treeObjs])
    trees = dict([(name, list()) for name in treeobjs])

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
            for elem in coords:
                trees[treetype].append(elem)
        tileworld = mclevel.MCInfdevOldLevel(tiledir, create=False)
        world.copyBlocksFrom(tileworld, tileworld.bounds, tileworld.bounds.origin)
        tileworld = False

    # plant trees in our world
    treeblocks = []
    treedatas = []
    for tree in trees:
        coords = trees[tree]
        for coord in coords:
            (blocks, datas) = treeobjs[tree](coord)
            treeblocks += blocks
            treedatas += datas
    [ world.setBlockAt(x, y, z, materialNamed(block)) for (x, y, z, block) in treeblocks if block != 'Air' ]
    [ world.setBlockDataAt(x, y, z, data) for (x, y, z, data) in treedatas if data != 0 ]

    # tie up loose ends
    setspawnandsave(world, peak)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

