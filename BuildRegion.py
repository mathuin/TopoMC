#!/usr/bin/env python

from newregion import Region
from newtile import Tile
import sys
import argparse
import os
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

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

    # set the inverse distance trees first
    myRegion.lcds = myRegion.ds(myRegion.lclayer)
    myRegion.elds = myRegion.ds(myRegion.ellayer)
    myRegion.lcidt = Tile.getIDT(myRegion.lcds, nodata=11)
    myRegion.elidt = Tile.getIDT(myRegion.elds, vscale=myRegion.scale)

    # generate individual tiles
    for tilex in xrange(myRegion.txmin, myRegion.txmax):
        for tiley in xrange(myRegion.tymin, myRegion.tymax):
            print "Generating tile for %d x %d..." % (tilex, tiley)
            myTile = Tile(myRegion, tilex, tiley)
            del myTile

    # generate overall world
    worlddir = os.path.join('Worlds', args.name)
    world = mclevel.MCInfdevOldLevel(worlddir, create=True)
    peak = [0, 0, 0]

    # merge individual worlds into it
    for tilex in xrange(myRegion.txmin, myRegion.txmax):
        for tiley in xrange(myRegion.tymin, myRegion.tymax):
            tiledir = os.path.join('Tiles', myRegion.name, '%dx%d' % (tilex, tiley))
            peakfile = file(os.path.join(tiledir, 'Tile.yaml'))
            newpeak = yaml.load(peakfile)
            peakfile.close()
            if (newpeak.peak[1] > peak[1]):
                peak = newpeak.peak
            tileworld = mclevel.MCInfdevOldLevel(tiledir, create=False)
            world.copyBlocksFrom(tileworld, tileworld.bounds, tileworld.bounds.origin)
            tileworld = False

    world.setPlayerPosition(tuple(peak))
    spawn = peak
    spawn[1] += 2
    world.setPlayerSpawnPosition(tuple(spawn))
    sizeOnDisk = 0
    # NB: numchunks is calculable = (region.tilesize/chunkWidth)*(region.tilesize/chunkWidth)
    numchunks = 0
    for i, cPos in enumerate(world.allChunks, 1):
        ch = world.getChunk(*cPos);
        numchunks += 1
        sizeOnDisk += ch.compressedSize();
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

