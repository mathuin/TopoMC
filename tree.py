# tree module
from random import random, randint
from mcmap import sealevel, setBlockAt, setBlockDataAt
from math import fabs, sqrt
from pymclevel.materials import alphaMaterials
from itertools import product
from multinumpy import SharedMemArray
from multiprocessing import Value
from numpy import zeros, int32

# tree constants
treeProb = 0.001

# tree statistics
# last two here need to be multiprocessor friendly
treeType = {
    0 : "cactus",
    1 : "regular",
    2 : "redwood",
    3 : "birch"
    }
treeCount = SharedMemArray(zeros((4),dtype=int32))
treeTotal = Value('i', 0)

def printTreeStatistics():
    print 'Tree statistics (%d total):' % treeTotal.value
    treeCountArr = treeCount.asarray()
    treeTuples = [(treeType[index], treeCountArr[index]) for index in treeCountArr if treeCountArr[index] > 0]
    for key, value in sorted(treeTuples, key=lambda tree: tree[1], reverse=True):
        treePercent = round((value*10000)/treeTotal.value)/100.0
        print '  %d (%.2f%%): %s' % (value, treePercent, key)

def placeTree(x, z, elevval, probFactor, treeType):
    chance = random()
    if (chance < treeProb*probFactor):
        if (treeType == -1):
            # cactus
            height = 3
        elif (treeType == 0):
            # regular
            height = randint(4, 6)
        elif (treeType == 1):
            # redwood
            height = randint(10, 12)
        elif (treeType == 2):
            # birch
            height = randint(7, 9)
        makeTree(x, z, elevval, height, treeType)

# actually places leaves and tree
def makeTree(x, z, elevval, height, treeType):
    global treeTotal
    base = sealevel+elevval
    maxleafheight = height+2
    trunkheight = 3
    leafheight = maxleafheight-trunkheight
    if (treeType == -1):
        [setBlockAt(x, sealevel+elevval+y, z, 'Cactus') for y in xrange(3)]
    else:
        for y in xrange(base,base+trunkheight):
            # FIXME: sigh, 'Tree trunk' doesn't work
            setBlockAt(x, y, z, alphaMaterials.names[17])
            setBlockDataAt(x, y, z, treeType)
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
                
    # increment tree count
    treeCountArr = treeCount.asarray()
    treeCountArr[treeType+1] += 1
    treeTotal.value += 1
