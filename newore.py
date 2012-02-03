# ore module
from __future__ import division
from random import random
from math import pi, ceil
from scipy.special import cbrt
from itertools import product

class Ore:
    """Each type of ore will be an instance of this class."""

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
        x0 = random()
        y0 = random()
        z0 = random()
        v0 = 4/3 * pi * x0 * y0 * z0
        # scale to match volume and round up
        scale = cbrt(self.size / v0)
        x1 = int(ceil(scale * x0))
        y1 = int(ceil(scale * y0))
        z1 = int(ceil(scale * z0))
        # generate ranges
        xr = xrange(int(-1 * x1), int(x1))
        yr = xrange(-1 * y1, y1)
        zr = xrange(-1 * z1, z1)
        # calculate max distance from center
        dist = self.size / (4/3 * pi)
        # calculate ellipsoid
        oreCoords = [ [mcx+x, mcy+y, mcz+z] for x, y, z in product(xr, yr, zr) if x*y*z <= dist ]
        return oreCoords
        
oreObjs = [
    Ore('Dirt', 7, 20, 32),
    Ore('Gravel', 7, 10, 32),
    Ore('Coal Ore', 7, 20, 16),
    Ore('Iron Ore', 6, 20, 8),
    Ore('Gold Ore', 5, 2, 8),
    Ore('Diamond Ore', 4, 1, 7),
    Ore('Redstone Ore', 4, 8, 7),
    Ore('Lapis Lazuli Ore', 4, 3, 7) ]

oreDQ = set([ore.name for ore in oreObjs] + ['Air', 'Water', 'Water (active)', 'Lava', 'Lava (active)', 'Bedrock'])
