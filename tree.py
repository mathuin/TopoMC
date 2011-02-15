# tree module
from __future__ import division
from random import random, randint
from mcmap import sealevel, setBlockAt, setBlockDataAt
from math import fabs, sqrt, ceil
from pymclevel.materials import alphaMaterials
from itertools import product
from multinumpy import SharedMemArray
from multiprocessing import Value
from numpy import zeros, int64, fromfunction

# tree constants
treeProb = 0.001
# If a tree canopy is about 20 units in area, then three trees 
# in a 10x10 area would provide about 60% coverage.
forestProb = 0.03

# maximum distance from the trunk
treeWidth = 3
sumSquares = fromfunction(lambda i, j: ((i-treeWidth)*(i-treeWidth)+(j-treeWidth)*(j-treeWidth)), (treeWidth*2+1, treeWidth*2+1), dtype=int64)

# leaf pattern functions
def regularPattern(x, z, y, maxy):
    ydist = min(y, maxy-y)
    return (sumSquares[ydist, ydist] < sumSquares[x, z])

def redwoodPattern(x, z, y, maxy):
    if (y == maxy):
        sawtooth = 1
    else:
        sawtooth = (maxy-y)%3+2
    return (sumSquares[sawtooth, sawtooth] < sumSquares[x, z])

def birchPattern(x, z, y, maxy):
    if (y == maxy):
        fromTop = 1
    else:
        fromTop = ceil((maxy-y)/3)
    return (sumSquares[fromTop, fromTop] < sumSquares[x, z])

def shrubPattern(x, z, y, maxy):
    return (sumSquares[x, z] < 3)

# tree statistics
treeType = {
    0 : 'Cactus',
    1 : 'Regular',
    2 : 'Redwood',
    3 : 'Birch',
    4 : 'Shrub'
    }
treeCount = {}
for key in treeType.keys():
    treeCount[key] = Value('i', 0)
#treeTotal = Value('i', 0)
# min height, max height, trunk height
treeHeight = [[3, 3, 3], [5, 7, 3], [7, 9, 3], [6, 8, 3], [2, 4, 1]]
leafPattern = [None, regularPattern, redwoodPattern, birchPattern, shrubPattern]

def printTreeStatistics():
    treeTuples = [(treeType[index], treeCount[index].value) for index in treeCount if treeCount[index].value > 0]
    treeTotal = sum([treeTuple[1] for treeTuple in treeTuples])
    print 'Tree statistics (%d total):' % treeTotal
    for key, value in sorted(treeTuples, key=lambda tree: tree[1], reverse=True):
        treePercent = (value*100)/treeTotal
        print '  %d (%.2f%%): %s' % (value, treePercent, key)

def placeTree(x, z, elevval, probFactor, treeName):
    chance = random()
    if (chance < probFactor):
        treeNum = [key for key in treeType if treeType[key] == treeName][0]
        makeTree(x, z, elevval, treeNum)

def makeTree(x, z, elevval, treeNum):
    testMonkey = True
    base = sealevel+elevval
    height = randint(treeHeight[treeNum][0], treeHeight[treeNum][1])
    leafbottom = base+treeHeight[treeNum][2]
    maxleafheight = base+height+1
    leafheight = maxleafheight-leafbottom
    # special case cactus!
    if (treeNum == 0):
        [setBlockAt(x, base+y, z, 'Cactus') for y in xrange(height)]
    else:
        leafxzrange = xrange(0-treeWidth,sumSquares.shape[0]-treeWidth)
        leafyrange = xrange(leafheight+1)
        for leafx, leafz, leafy in product(leafxzrange, leafxzrange, leafyrange):
            if leafPattern[treeNum](leafx, leafz, leafy, leafheight):
                setBlockAt(x+leafx, leafbottom+leafy, z+leafz, 'Leaves')
                setBlockDataAt(x+leafx, leafbottom+leafy, z+leafz, treeNum-1)
        for y in xrange(base,base+height):
            # FIXME: sigh, 'Tree trunk' doesn't work
            setBlockAt(x, y, z, alphaMaterials.names[17])
            setBlockDataAt(x, y, z, treeNum-1)
    # increment tree count
    treeCount[treeNum].value += 1
    #treeTotal.value += 1
