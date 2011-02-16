# tree module
from __future__ import division
from random import random, randint
from mcmap import sealevel, setBlockAt, setBlockDataAt
from pymclevel.materials import alphaMaterials
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
treeWidth = 3
leafDistance = fromfunction(lambda i, j: sqrt((i-treeWidth)*(i-treeWidth)+(j-treeWidth)*(j-treeWidth)), (treeWidth*2+1, treeWidth*2+1), dtype=float32)
# [[ 4.24, 3.60, 3.16, 3.00, 3.16, 3.60, 4.24],
#  [ 3.60, 2.82, 2.23, 2.00, 2.23, 2.82, 3.60],
#  [ 3.16, 2.23, 1.41, 1.00, 1.41, 2.23, 3.16],
#  [ 3.00, 2.00, 1.00, 0.00, 1.00, 2.00, 3.00],
#  [ 3.16, 2.23, 1.41, 1.00, 1.41, 2.23, 3.16],
#  [ 3.60, 2.82, 2.23, 2.00, 2.23, 2.82, 3.60],
#  [ 4.24, 3.60, 3.16, 3.00, 3.16, 3.60, 4.24]]

print leafDistance

# leaf pattern functions 
def regularPattern(x, z, y, maxy):
    if (leafDistance[x, z] <= 2.5):
        if (y == 0):
            print "regular: x=%d, z=%d, ld=%.2f" % (x, z, leafDistance[x, z])
        return True
    else:
        return False

def redwoodPattern(x, z, y, maxy):
    if (leafDistance[x, z] < 2.5):
        return True
    else:
        return False

def birchPattern(x, z, y, maxy):
    if (leafDistance[x, z] < 2.5):
        return True
    else:
        return False

def shrubPattern(x, z, y, maxy):
    if (leafDistance[x, z] < 2.5):
        return True
    else:
        return False

def palmPattern(x, z, y, maxy):
    return (y == maxy)

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
        lxzrange = xrange(leafDistance.shape[0])
        lyrange = xrange(leafheight+1)
        for leafx, leafz, leafy in product(lxzrange, lxzrange, lyrange):
            if leafPattern[treeNum](leafx, leafz, leafy, leafheight):
                setBlockAt(x+leafx-treeWidth, leafbottom+leafy, z+leafz-treeWidth, 'Leaves')
                setBlockDataAt(x+leafx-treeWidth, leafbottom+leafy, z+leafz-treeWidth, treeNum-1)
        for y in xrange(base,base+height):
            # FIXME: sigh, 'Tree trunk' doesn't work
            setBlockAt(x, y, z, alphaMaterials.names[17])
            setBlockDataAt(x, y, z, treeNum-1)
    # increment tree count
    treeCount[treeNum].value += 1
    #treeTotal.value += 1
