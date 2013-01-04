# ore module
from __future__ import division
from random import randint
from math import pi
from scipy.special import cbrt
from itertools import product
from utils import materialNamed

# http://www.minecraftforum.net/topic/25886-elites-of-minecraft-the-miner-first-ore-loss-calculated/ (must be logged in)


class Ore:
    """Each type of ore will be an instance of this class."""

    # what ID is stone?
    # we use 'end stone' actually since 'stone' might be in a schematic
    stoneID = materialNamed('End Stone')

    def __init__(self, name, depth=None, rounds=None, size=None):
        # nobody checks names
        # NB: ore names are block names too, consider fixing this
        self.name = name
        self.depth = depth
        self.rounds = rounds
        self.size = size

    def __call__(self, coords):
        # generate ellipsoid values based on parameters
        (mcx, mcy, mcz) = coords
        # start with random radius-like values
        x0 = randint(1, 4)
        y0 = randint(1, 4)
        z0 = randint(1, 4)
        v0 = 4/3 * pi * x0 * y0 * z0
        # scale to match volume and round up
        scale = cbrt(self.size / v0)
        x1 = int(round(scale * x0))
        y1 = int(round(scale * y0))
        z1 = int(round(scale * z0))
        # pre-calculate squares
        x2 = x1 * x1
        y2 = y1 * y1
        z2 = z1 * z1
        # generate ranges
        xr = xrange(-1 * x1, x1)
        yr = xrange(-1 * y1, y1)
        zr = xrange(-1 * z1, z1)
        # calculate ellipsoid
        oreCoords = [[mcx+x, mcy+y, mcz+z] for x, y, z in product(xr, yr, zr) if x*x/x2+y*y/y2+z*z/z2 <= 1]
        # if len(oreCoords) > self.size+2:
        #     print "warning: oreCoords larger than self.size -- %d > %d" % (len(oreCoords), self.size)
        # if len(oreCoords) < self.size-2:
        #     print "warning: oreCoords smaller than self.size -- %d < %d" % (len(oreCoords), self.size)
        return oreCoords

    @staticmethod
    def placeoreintile(tile):
        # strictly speaking, this should be in class Tile somehow
        oreobjs = dict([(ore.name, ore) for ore in oreObjs])
        tile.ores = dict([(name, list()) for name in oreobjs])

        for ore in oreobjs:
            extent = cbrt(oreobjs[ore].size)*2
            maxy = pow(2, oreobjs[ore].depth)
            numrounds = int(oreobjs[ore].rounds * (tile.size/16) * (tile.size/16))
            oreID = materialNamed(oreobjs[ore].name)
            for dummy in xrange(numrounds):
                orex = randint(0, tile.size)
                orey = randint(0, maxy)
                orez = randint(0, tile.size)
                coords = [orex+tile.mcoffsetx, orey, orez+tile.mcoffsetz]
                if (orex < extent or (tile.size-orex) < extent or orez < extent or (tile.size-orez) < extent):
                    try:
                        tile.ores[ore]
                    except KeyError:
                        tile.ores[ore] = []
                    tile.ores[ore].append(coords)
                else:
                    for x, y, z in oreobjs[ore](coords):
                        if tile.world.blockAt(x, y, z) == Ore.stoneID:
                            tile.world.setBlockAt(x, y, z, oreID)

    @staticmethod
    def placeoreinregion(ores, oreobjs, world):
        for ore in ores:
            oreID = materialNamed(oreobjs[ore].name)
            for x, y, z in ores[ore]:
                if world.blockAt(x, y, z) == Ore.stoneID:
                    world.setBlockAt(x, y, z, oreID)

oreObjs = [
    Ore('Dirt', 7, 20, 32),
    Ore('Gravel', 7, 10, 32),
    Ore('Coal Ore', 7, 20, 16),
    Ore('Iron Ore', 6, 20, 8),
    Ore('Gold Ore', 5, 2, 8),
    Ore('Emerald Ore', 5, 1, 8),
    Ore('Diamond Ore', 4, 1, 7),
    Ore('Redstone Ore', 4, 8, 7),
    Ore('Lapis Lazuli Ore', 4, 3, 7)]
