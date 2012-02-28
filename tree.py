# tree module
from __future__ import division
from math import hypot
import numpy
from random import randint
from itertools import product
from utils import materialNamed

class Tree:
    """Each type of tree will be an instance of this class."""

    # constants
    treeProb = 0.001

    # if a tree canopy is about 20 units in area, then three trees in
    # a 10x10 area would provide about 60% coverage.
    forestProb = 0.03

    # maximum distance from the trunk
    treeWidth = 2

    # leaf distance from the trunk
    leafDistance = numpy.array([[hypot(i-treeWidth,j-treeWidth) for i in xrange(treeWidth*2+1)] for j in xrange(treeWidth*2+1)], dtype=numpy.float32)

    def __init__(self, name, pattern=None, data=None, heights=None):
        # nobody checks names
        self.name = name
        # only leafy trees have patterns
        self.pattern = pattern
        # data value is integer for leafy trees and string for non-leafy trees
        if self.pattern != None:
            if type(data) is int:
                self.data = data
            else:
                raise AttributeError, "leafy trees require integer values for data: %d" % data
        else:
            if type(data) is str:
                self.data = data
            else:
                raise AttributeError, "non-leafy trees require string values for data: %d" % data
        # heights (max, min, trunk)
        if type(heights) is list and len(heights) is 3 and all([type(elem) is int for elem in heights]):
            self.heights = heights
        else:
            raise AttributeError, "heights array is not right: ", heights

    # call routine places a tree in a particular location
    def __call__(self, coords):
        """Places tree in a particular location."""
        # coords: [x, y, z]
        # __call__ returns blocks, datas
        # which are lists of x, y, z, value tuples
        (x, base, z) = coords
        height = randint(self.heights[0], self.heights[1])
        leafbottom = base + self.heights[2]
        maxleafheight = base + height + 1
        leafheight = maxleafheight - leafbottom
        # cactus and sugarcane have no patterns
        if self.pattern == None:
            blocks = [ (x, base+y, z, self.data) for y in xrange(height) ]
            datas = []
        else:
            blocks = []
            datas = []
            lxzrange = xrange(Tree.leafDistance.shape[0])
            lyrange = xrange(leafheight)
            for leafx, leafz, leafy in product(lxzrange, lxzrange, lyrange):
                myleafx = x+leafx-Tree.treeWidth
                myleafy = leafbottom+leafy
                myleafz = z+leafz-Tree.treeWidth
                if self.pattern(leafx, leafy, leafz, leafheight-1):
                    blocks.append((myleafx, myleafy, myleafz, 'Leaves'))
                    datas.append((myleafx, myleafy, myleafz, self.data))
            for y in xrange(base,base+height):
                blocks.append((x, y, z, 'Wood'))
                datas.append((x, y, z, self.data))
        return blocks, datas

    @staticmethod
    def placetreeintile(tile, tree, mcx, mcy, mcz):
        coords = [mcx, mcy, mcz]
        myx = tile.mcoffsetx - mcx
        myz = tile.mcoffsetx - mcz
        if (myx < Tree.treeWidth+1 or (tile.size-myx) < Tree.treeWidth+1 or
            myz < Tree.treeWidth+1 or (tile.size-myz) < Tree.treeWidth+1):
            # tree is too close to the edge, plant it later
            try:
                tile.trees[tree]
            except KeyError:
                tile.trees[tree] = []
            tile.trees[tree].append(coords)
        else:
            # plant it now!
            (blocks, datas) = treeobjs[tree](coords)
            [ tile.world.setBlockAt(x, y, z, materialNamed(block)) for (x, y, z, block) in blocks if block != 'Air' ]
            [ tile.world.setBlockDataAt(x, y, z, data) for (x, y, z, data) in datas if data != 0 ]

    @staticmethod
    def placetreesinregion(trees, treeobjs, world):
        for tree in trees:
            coords = trees[tree]
            for coord in coords:
                (blocks, datas) = treeobjs[tree](coord)
                [ world.setBlockAt(x, y, z, materialNamed(block)) for (x, y, z, block) in blocks if block != 'Air' ]
                [ world.setBlockDataAt(x, y, z, data) for (x, y, z, data) in datas if data != 0 ]

treeObjs = [ 
    Tree('Cactus', None, 'Cactus', [3, 3, 3]), 
    Tree('Sugar Cane', None, 'Sugar Cane', [3, 3, 3]), 
    Tree('Regular', (lambda x, y, z, maxy: Tree.leafDistance[x, z] <= (maxy-y+2)*Tree.treeWidth/maxy), 0, [5, 7, 2]),
    Tree('Redwood', (lambda x, y, z, maxy: Tree.leafDistance[x, z] <= 0.75*((maxy-y+1)%(Tree.treeWidth+1)+1)), 1, [9, 11, 2]),
    Tree('Birch', (lambda x, y, z, maxy: Tree.leafDistance[x, z] <= 1.2*(min(y, maxy-y+1)+1)), 2, [7, 9, 2]),
    Tree('Shrub', (lambda x, y, z, maxy: Tree.leafDistance[x, z] <= 1.5*(maxy-y+1)/maxy+0.5), 3, [1, 3, 0]),
    Tree('Palm', (lambda x, y, z, maxy: y == maxy and Tree.leafDistance[x, z] < Tree.treeWidth+1), 0, [5, 7, 2]) ]
