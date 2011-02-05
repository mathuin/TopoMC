# tree module
from random import random, randint
from mcmap import sealevel, setBlockAt, setBlockDataAt
from math import fabs, sqrt

# tree constants
treeProb = 0.001

# tree statistics
treeType = {}
treeCount = {}
treeTotal = 0

def populateTreeVariables(treeType, treeCount):
    # index starts with zero, cactus is -1
    treeMetaType = {
        0 : "cactus",
        1 : "regular",
        2 : "redwood",
        3 : "birch"
        }
            
    for i in treeMetaType:
        treeType[i] = treeMetaType[i]
        treeCount[i] = 0

def printTreeStatistics():
    print 'Tree statistics (%d total):' % treeTotal
    treeTuples = [(treeType[index], treeCount[index]) for index in treeCount if treeCount[index] > 0]
    for key, value in sorted(treeTuples, key=lambda tree: tree[1], reverse=True):
        treePercent = round((value*10000)/treeTotal)/100.0
        print '  %d (%.2f): %s' % (value, treePercent, key)

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
    maxleafheight = height+1
    trunkheight = 1
    if (treeType == -1):
        [setBlockAt(x, sealevel+elevval+y, z, 'Cactus') for y in xrange(3)]
    else:
        for index in xrange(maxleafheight):
            y = sealevel+elevval+index
            if (index > trunkheight):
                curleafheight = index-trunkheight
                totop = (maxleafheight-trunkheight)-curleafheight
                if (curleafheight > totop):
                    curleafwidth = totop+1
                else:
                    curleafwidth = curleafheight
                    xminleaf = x - curleafwidth
                    xmaxleaf = x + curleafwidth
                    zminleaf = z - curleafwidth
                    zmaxleaf = z + curleafwidth
                    for xindex in xrange(xminleaf, xmaxleaf+1):
                        for zindex in xrange(zminleaf, zmaxleaf+1):
                            deltax = fabs(xindex-x)
                            deltaz = fabs(zindex-z)
                            sumsquares = pow(deltax,2)+pow(deltaz,2)
                            if (sqrt(sumsquares) < curleafwidth*.75):
                                setBlockAt(xindex, y, zindex, 'Leaves')
                                setBlockDataAt(xindex, y, zindex, treeType)
            if (index < height):
                setBlockAt(x, y, z, 'Wood')
                setBlockDataAt(x, y, z, treeType)
                
    # increment tree count
    treeCount[treeType+1] += 1
    treeTotal += 1

# initialize
populateTreeVariables(treeType, treeCount)
