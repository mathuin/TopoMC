# it is time to place some ore

from __future__ import division
from random import randint
from multiprocessing import Value
from time import clock
from scipy.special import cbrt
from math import pi
from mcmap import getBlockAt, getBlocksAt, setBlocksAt, arrayBlocks
# for minX, minZ, maxX, and maxZ
import mcmap
from multiprocessing import Pool
from itertools import product

# http://www.minecraftwiki.net/wiki/Ore
oreType = {
    0: 'Dirt',
    1: 'Gravel',
    2: 'Coal Ore',
    3: 'Iron Ore',
    4: 'Gold Ore', 
    5: 'Diamond Ore',
    6: 'Redstone Ore',
    7: 'Lapis Lazuli Ore'
}
oreDepth = [7, 7, 7, 6, 5, 4, 4, 4]
# http://www.minecraftforum.net/viewtopic.php?f=35&t=28299
# "rounds" is how many times per chunk a deposit is generated
# "size" is the rough max size of a deposit
# user guide says (size/4)*(size/4)*(2+size/8)
# I am insane. I model an ideal ellipsoid.  Yay!
# BTW: LL round value of 3 a guess.
oreRounds = [20, 10, 20, 20, 2, 1, 8, 3]
oreSize = [32, 32, 16, 8, 8, 7, 7, 7]
# statistics tracks nodes and veins
oreNodeCount = {}
oreVeinCount = {}
for key in oreType.keys():
    oreNodeCount[key] = Value('i', 0)
    oreVeinCount[key] = Value('i', 0)
# any ore that tries to replace these blocks is hereby disqualified
oreDQ = set(oreType.values() + ['Air', 'Water (still)', 'Water (active)', 'Lava (still)', 'Lava (active)', 'Bedrock'])

# actually deposits the ore
def processOre(oreName, minY, maxY, maxExtent):
    "Deposits ore in a random part of the ground."
    clumpX = randint(int(maxExtent*100),int(maxExtent*900))/1000
    clumpY = randint(int(maxExtent*100),int(maxExtent*900))/1000
    clumpZ = randint(int(maxExtent*100),int(maxExtent*900))/1000
    clumpScale = ((4/3)*pi*clumpX*clumpY*clumpZ)/oreSize[oreName]
    # dunno about these boundaries
    clumpX = min(max(0.5, (clumpX/clumpScale)), maxExtent)
    clumpY = min(max(0.5, (clumpY/clumpScale)), maxExtent)
    clumpZ = min(max(0.5, (clumpZ/clumpScale)), maxExtent)
    oreX = randint(int(mcmap.minX+clumpX),int(mcmap.maxX-clumpX))
    oreY = randint(int(minY+clumpY),int(maxY-clumpY))
    oreZ = randint(int(mcmap.minZ+clumpZ),int(mcmap.maxZ-clumpZ))
    oXrange = xrange(int(0-clumpX), int(clumpX+1))
    oYrange = xrange(int(0-clumpY), int(clumpY+1))
    oZrange = xrange(int(0-clumpZ), int(clumpZ+1))
    clumpX2 = clumpX*clumpX
    clumpY2 = clumpY*clumpY
    clumpZ2 = clumpZ*clumpZ
    # anything in the ellipsoid except air/water/lava and other ores
    oreCoords = [[oreX+x, oreY+y, oreZ+z] for x,y,z in product(oXrange, oYrange, oZrange) if ((x*x)/clumpX2+(y*y)/clumpY2+(z*z)/clumpZ2<=1) and getBlockAt(oreX+x, oreY+y, oreZ+z) not in oreDQ]
    oreBlocks = getBlocksAt(oreCoords)
    # all it takes is one Stone and we're in
    # FIXME: should start over if oreCoords has a len of 0
    if ('Stone' in oreBlocks):
        oreNodeCount[oreName].value += len(oreCoords)
        oreVeinCount[oreName].value += 1
        setBlocksAt([x, y, z, oreType[oreName]] for x, y, z in oreCoords)

def processOrestar(args):
    return processOre(*args)

def processOres(oreName, minY, maxY, maxExtent, numRounds):
    if (mcmap.processes == 1):
        bleah = [processOre(oreName, minY, maxY, maxExtent) for count in xrange(numRounds)]
    else:
        pool = Pool(mcmap.processes)
        tasks = [(oreName, minY, maxY, maxExtent) for count in xrange(numRounds)]
        results = pool.imap_unordered(processOrestar, tasks)
        bleah = [x for x in results]
    return None

# whole-world approach
def placeOre():
    placestart = clock()
    # FIXME: calculate this instead?
    numChunks = len(arrayBlocks.keys())
    for ore in oreType.keys():
        print "Adding %s now..." % (oreType[ore])
        # everything starts on the bottom
        # only doing common pass here
        minY = 0
        maxY = pow(2,oreDepth[ore])
        maxExtent = cbrt(oreSize[ore])/2
        numRounds = int(oreRounds[ore]*numChunks)
        processOres(ore, minY, maxY, maxExtent, numRounds)
        print "... %d veins totalling %d units placed." % (oreVeinCount[ore].value, oreNodeCount[ore].value)
    print "finished in %.2f seconds." % (clock()-placestart)

def printStatistics():
    oreTuples = [(oreType[index], oreNodeCount[index].value, oreVeinCount[index].value) for index in oreNodeCount if oreNodeCount[index].value > 0]
    oreNodeTotal = sum([oreTuple[1] for oreTuple in oreTuples])
    oreVeinTotal = sum([oreTuple[2] for oreTuple in oreTuples])
    print 'Ore statistics (%d total nodes, %d total veins):' % (oreNodeTotal, oreVeinTotal)
    for key, value, value2 in sorted(oreTuples, key=lambda ore: ore[1], reverse=True):

        print '  %d (%d veins): %s' % (value, value2, key)

