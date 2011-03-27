# tree module
from __future__ import division
from random import random, randint
from mcmap import sealevel, setBlockAt, setBlockDataAt
import mcmap # for minX, minZ, maxX, maxZ
from itertools import product
from multinumpy import SharedMemArray
from multiprocessing import Value
from numpy import zeros, int64, fromfunction, float32, sqrt

# tree constants
treeProb = 0.001
# If a tree canopy is about 20 units in area, then three trees 
# in a 10x10 area would provide about 60% coverage.
forestProb = 0.03

# maximum distance from the trunk
treeWidth = 2
leafDistance = fromfunction(lambda i, j: sqrt((i-treeWidth)*(i-treeWidth)+(j-treeWidth)*(j-treeWidth)), (treeWidth*2+1, treeWidth*2+1), dtype=float32)
# [[ 4.24, 3.60, 3.16, 3.00, 3.16, 3.60, 4.24],
#  [ 3.60, 2.82, 2.23, 2.00, 2.23, 2.82, 3.60],
#  [ 3.16, 2.23, 1.41, 1.00, 1.41, 2.23, 3.16],
#  [ 3.00, 2.00, 1.00, 0.00, 1.00, 2.00, 3.00],
#  [ 3.16, 2.23, 1.41, 1.00, 1.41, 2.23, 3.16],
#  [ 3.60, 2.82, 2.23, 2.00, 2.23, 2.82, 3.60],
#  [ 4.24, 3.60, 3.16, 3.00, 3.16, 3.60, 4.24]]

# leaf pattern functions 
def regularPattern(x, z, y, maxy):
    return (leafDistance[x, z] <= (maxy-y+2)*treeWidth/maxy)

def redwoodPattern(x, z, y, maxy):
    return (leafDistance[x, z] <= 0.75*((maxy-y+1)%(treeWidth+1)+1))

def birchPattern(x, z, y, maxy):
    return (leafDistance[x, z] <= 1.2*(min(y, maxy-y+1)+1))

def shrubPattern(x, z, y, maxy):
    return (leafDistance[x, z] <= 1.5*(maxy-y+1)/maxy+0.5)

def palmPattern(x, z, y, maxy):
    return (y == maxy and leafDistance[x, z] < treeWidth+1)

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
# min height, max height, trunk height
treeHeight = [[3, 3, 3], [5, 7, 2], [9, 11, 2], [7, 9, 2], [1, 3, 0]]
leafPattern = [None, regularPattern, redwoodPattern, birchPattern, shrubPattern]

def printStatistics():
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
    base = sealevel+elevval
    height = randint(treeHeight[treeNum][0], treeHeight[treeNum][1])
    leafbottom = base+treeHeight[treeNum][2]
    maxleafheight = base+height+1
    leafheight = maxleafheight-leafbottom
    # special case cactus!
    if (treeNum == 0):
        [setBlockAt(x, base+y, z, 'Cactus') for y in xrange(height)]
    else:
        lxzrange = xrange(leafDistance.shape[0])
        lyrange = xrange(leafheight)
        for leafx, leafz, leafy in product(lxzrange, lxzrange, lyrange):
            myleafx = max(min(x+leafx-treeWidth, mcmap.minX), mcmap.maxX)
            myleafy = leafbottom+leafy
            myleafz = max(min(z+leafz-treeWidth, mcmap.minZ), mcmap.maxZ)
            if leafPattern[treeNum](leafx, leafz, leafy, leafheight-1):
                setBlockAt(myleafx, myleafy, myleafz, 'Leaves')
                setBlockDataAt(myleafx, myleafy, myleafz, treeNum-1)
        for y in xrange(base,base+height):
            # FIXME: sigh, 'Tree trunk' doesn't work
            setBlockAt(x, y, z, 'Wood')
            setBlockDataAt(x, y, z, treeNum-1)
    # increment tree count
    treeCount[treeNum].value += 1
