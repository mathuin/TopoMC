#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
from newregion import Region
from newtile import Tile
from newutils import setspawnandsave
import sys
import argparse
import os
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from multiprocessing import Pool

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
    print "Now building %d tiles" % ((myRegion.txmax-myRegion.txmin)*(myRegion.tymax-myRegion.tymin))
    tiles = [(myRegion, tilex, tiley) for tilex in xrange(myRegion.txmin, myRegion.txmax) for tiley in xrange(myRegion.tymin, myRegion.tymax)]
    # single process version - works
    for tile in tiles:
        (myRegion, tilex, tiley) = tile
        print "building tile %d, %d" % (tilex-myRegion.txmin, tiley-myRegion.tymin)
        myTile = Tile(myRegion, tilex, tiley)
        mypeak = myTile.build()
        if (mypeak[1] > peak[1]):
            print "new peak: ", mypeak
            peak = mypeak
        myWorld = mclevel.MCInfdevOldLevel(myTile.tiledir, create=False)
        world.copyBlocksFrom(myWorld, myWorld.bounds, myWorld.bounds.origin)

    # tie up loose ends
    setspawnandsave(world, peak)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

