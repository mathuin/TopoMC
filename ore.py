# it is time to place some ore

from __future__ import division
from pymclevel import materials
from random import randint
from multiprocessing import Value
from time import clock
from mcmap import getBlocksAt, setBlocksAt, arrayBlocks

# http://www.minecraftwiki.net/wiki/Ore
oreType = {
    0: 'Dirt',
    1: 'Gravel',
    2: 'Coal',
    3: 'Iron',
    4: 'Gold', 
    5: 'Diamond',
    6: 'Redstone',
    7: 'Lapis Lazuli'
}
oreDepth = [7, 7, 7, 6, 5, 4, 4, 4]
oreValue = [3, 13, 16, 15, 14, 56, 73, 21]
# http://www.minecraftforum.net/viewtopic.php?f=35&t=28299
# "rounds" is how many times per chunk a deposit is generated
# "size" is the rough max size of a deposit
# (size/4)*(size/4)*(2+size/8)
# "size" is the rough max size of a deposit
# (size/4)*(size/4)*(2+size/8)
# LL round value of 3 a guess.
oreRounds = [20, 10, 20, 20, 2, 1, 8, 3]
oreSize = [32, 32, 16, 8, 8, 7, 7, 7]
# statistics soon
# this is a vein count -- make a node count soon enough
oreCount = {}
for key in oreType.keys():
    oreCount[key] = Value('i', 0)

# whole-world approach
def placeOre(minX, minZ, maxX, maxZ):
    placestart = clock()
    print "inputs = %d, %d, %d, %d" % (minX, minZ, maxX, maxZ) 
    numChunks = len(arrayBlocks.keys())
    for ore in oreType.keys():
        print "Adding %s now..." % (oreType[ore])
        # this math feels wrong, but I don't want to do cube roots either
        # FIXME: add randomness later
        # idea for randomness -- %age of distance from 'center point'?
        clumpX = int(oreSize[ore]/4)
        clumpZ = int(oreSize[ore]/4)
        clumpY = int(2+oreSize[ore]/8)
        # volume is x^2/16*(16+x)/8=(x^3+16x2)/128
        # which equals 8.8 for x=7, 12 for x=8, and 2.5 for x=4
        numRounds = int(oreRounds[ore]*numChunks)
        for round in xrange(numRounds):
            # choose a triple
            oreX = randint(minX,maxX-clumpX)
            oreZ = randint(minZ,maxZ-clumpZ)
            oreY = randint(0,128-clumpY)
            #print "  round #%d: trying %d, %d, %d..." % (round, oreX, oreY, oreZ)
            # now that we have a point, get blocks in range
            oreCoords = [[x, y, z] for x in xrange(oreX, oreX+clumpX) for z in xrange(oreZ, oreZ+clumpZ) for y in xrange(oreY, oreY+clumpY)]
            # install ore unless there's something else there
            oreBlocks = getBlocksAt(oreCoords)
            # FIXME: currently excludes areas with other ores
            # consider not excluding if it's only the same ore
            if ('Stone' in oreBlocks and len(set(oreBlocks).intersection(set(oreType.values()))) == 0):
                #print "    success!"
                oreCount[ore].value += 1
                setBlocksAt([x, y, z, materials.names[oreValue[ore]]] for x, y, z in oreCoords)
        print "... %d veins placed." % oreCount[ore].value
    print "finished in %.2f seconds." % (clock()-placestart)

def printOreStatistics():
    oreTuples = [(oreType[index], oreCount[index].value) for index in oreCount if oreCount[index].value > 0]
    oreTotal = sum([oreTuple[1] for oreTuple in oreTuples])
    print 'Ore statistics (%d total):' % oreTotal
    for key, value in sorted(oreTuples, key=lambda ore: ore[1], reverse=True):
        orePercent = (value*100)/oreTotal
        print '  %d (%.2f%%): %s' % (value, orePercent, key)

