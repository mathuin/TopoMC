# tree module
from random import random, randint
from mcmap import sealevel, setBlockAt, setBlockDataAt
from math import fabs, sqrt
from pymclevel.materials import alphaMaterials
from itertools import product
from multinumpy import SharedMemArray
from multiprocessing import Value
from numpy import zeros, int64

# tree constants
treeProb = 0.001
# If a tree canopy is about 20 units in area, then three trees 
# in a 10x10 area would provide about 60% coverage.
forestProb = 0.03

# tree statistics
# last two here need to be multiprocessor friendly
treeType = {
    0 : "cactus",
    1 : "regular",
    2 : "redwood",
    3 : "birch",
    4 : "shrub"
    }
treeCount = {}
for key in treeType.keys():
    treeCount[key] = Value('i', 0)
treeTotal = Value('i', 0)

def printTreeStatistics():
    print 'Tree statistics (%d total):' % treeTotal.value
    treeTuples = [(treeType[index], treeCount[index].value) for index in treeCount if treeCount[index].value > 0]
    for key, value in sorted(treeTuples, key=lambda tree: tree[1], reverse=True):
        treePercent = round((value*10000)/treeTotal.value)/100.0
        print '  %d (%.2f%%): %s' % (value, treePercent, key)

def placeTree(x, z, elevval, probFactor, treeType):
    chance = random()
    if (chance < probFactor):
        makeTree(x, z, elevval, treeType)

# actually places leaves and tree
# trees may hit roof!
# need to watch for this
def makeTree(x, z, elevval, treeType):
    global treeTotal
    # FIXME: define leaf function somehow here
    # example redwood: _\\\
    #         regular: _/-\
    #         birch  : _|-\
    #         shrub  : -\     
    if (treeType == -1):
        # cactus
        height = 3
    elif (treeType == 0):
        # regular
        height = randint(5, 7)
    elif (treeType == 1):
        # redwood
        height = randint(7, 9)
    elif (treeType == 2):
        # birch
        height = randint(6, 8)
    elif (treeType == 3):
        # shrub
        height = randint(2, 4)
    base = sealevel+elevval
    maxleafheight = height+2
    trunkheight = 3
    leafheight = maxleafheight-trunkheight
    if (treeType == -1):
        [setBlockAt(x, sealevel+elevval+y, z, 'Cactus') for y in xrange(height)]
    else:
        for y in xrange(base+trunkheight,base+maxleafheight):
            curleafheight = y-(base+trunkheight)
            #curleafwidth = min(curleafheight,leafheight-curleafheight)
            # JMT: this makes a redwood-like leaf pattern
            curleafwidth = (leafheight-curleafheight)/2+1
            
            xminleaf = x - curleafwidth
            xmaxleaf = x + curleafwidth +1
            xrangeleaf = xrange(xminleaf, xmaxleaf)
            zminleaf = z - curleafwidth
            zmaxleaf = z + curleafwidth +1
            zrangeleaf = xrange(zminleaf, zmaxleaf)
            for xindex, zindex in product(xrangeleaf, zrangeleaf):
                if (sqrt(pow(xindex-x,2)+pow(zindex-z,2)) < 0.75*curleafwidth):
                    setBlockAt(xindex, y, zindex, 'Leaves')
                    setBlockDataAt(xindex, y, zindex, treeType)
        for y in xrange(base,base+height):
            # FIXME: sigh, 'Tree trunk' doesn't work
            setBlockAt(x, y, z, alphaMaterials.names[17])
            setBlockDataAt(x, y, z, treeType)
                
    # increment tree count
    treeCount[treeType+1].value += 1
    treeTotal.value += 1
