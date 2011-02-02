#!/usr/bin/env python

import sys
sys.path.append('..')
from pymclevel import mclevel
from time import clock
import Image
import numpy
import math
from pymclevel.box import BoundingBox
from random import random, randint
from multiprocessing import Pool, cpu_count

# constants
sealevel = 64
baseline = 32 # below here is just stone
filler = sealevel - baseline

# set maxMapHeight to a conservative value
maxMapHeight = 125 - sealevel

# these are outside the loop
# everyone wants the level
level = None
starttime = clock()

# processImage modifies these as it runs
maxelev = 0
maxbathy = 0
spawnx = 0
spawny = 0
spawnz = 0

# land cover statistics
lcType = {}
lcCount = {}
lcTotal = 0
treeType = {}
treeCount = {}
treeTotal = 0

# land cover constants
treeProb = 0.001

# inside the loop
def processImage(offset_x, offset_z):
    imagetime = clock()
    region = 'BlockIsland'
    imagedir = "Images/"+region
    lcimg = Image.open('%s/lc-%d-%d.gif' % (imagedir, offset_x, offset_z))
    elevimg = Image.open('%s/elev-%d-%d.gif' % (imagedir, offset_x, offset_z))
    bathyimg = Image.open('%s/bathy-%d-%d.gif' % (imagedir, offset_x, offset_z))

    lcarray = numpy.asarray(lcimg)
    elevarray = numpy.asarray(elevimg)
    bathyarray = numpy.asarray(bathyimg)

    (size_x, size_z) = lcarray.shape
    stop_x = offset_x+size_x
    stop_z = offset_z+size_z

    global maxelev
    global maxbathy

    # inform the user
    print 'Processing tile at position (%d, %d)...' % (offset_x, offset_z)

    # iterate over the image
    for x in xrange(size_x):
        for z in xrange(size_z):
            lcval = lcarray[x][z]
            elevval = elevarray[x][z]
            bathyval = bathyarray[x][z]
            real_x = offset_x + x
            real_z = offset_z + z
            if (elevval > maxMapHeight):
                print('oh no elevation ' + elevval + ' is too high')
                elevval = maxMapHeight
            if (elevval > maxelev):
                spawnx = real_x
                spawnz = real_z
                spawny = elevval
            if (bathyval > maxbathy):
                maxelev = bathyval

            processLcval(lcval, real_x, real_z, elevval, bathyval)
	
    # print out status
    print '... finished in %f seconds.' % (clock()-imagetime)

def processImagestar(args):
    return processImage(*args)

def populateLandCoverVariables(lcType, lcCount, treeType, treeCount):
    # first add all the text values for land covers
    # http://www.mrlc.gov/nlcd_definitions.php
    lcMetaType = {
        0 : "Unknown",
	11 : "Water",
	12 : "Ice/Snow",
	21 : "Developed/Open-Space",
	22 : "Developed/Low-Intensity",
	23 : "Developed/Medium-Intensity",
	24 : "Developed/High-Intensity",
	31 : "Barren Land",
	32 : "Unconsolidated Shore",
	41 : "Deciduous Forest",
	42 : "Evergreen Forest",
	43 : "Mixed Forest",
	51 : "Dwarf Scrub",
	52 : "Shrub/Scrub",
	71 : "Grasslands/Herbaceous",
	72 : "Sedge/Herbaceous",
	73 : "Lichens",
	74 : "Moss",
	81 : "Pasture/Hay",
	82 : "Cultivated Crops",
	90 : "Woody Wetlands",
	91 : "Palustrine Forested Wetlands",
	92 : "Palustrine Scrub/Shrub Wetlands",
	93 : "Estuarine Forested Wetlands",
	94 : "Estuarine Scrub/Shrub Wetlands",
	95 : "Emergent Herbaceous Wetlands",
	96 : "Palustrine Emergent Wetlands",
	97 : "Estuarine Emergent Wetlands",
	98 : "Palustrine Aquatic Bed",
	99 : "Estuarine Aquatic Bed"
        }
    
    for i in lcMetaType:
        lcType[i] = lcMetaType[i]
	lcCount[i] = 0
        
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
        
# process a given land cover value
def processLcval(lcval, x, z, elevval, bathyval):
    global lcTotal
    lcTotal += 1
    if (lcval not in lcType):
        print('unexpected value for land cover: ' + lcval)
        lcCount[0] += 1
        layers(x, z, elevval, 'Dirt')
    else:
        lcCount[lcval] += 1
        # http://www.mrlc.gov/nlcd_definitions.php
        if (lcval == 11):
            # water
            layers(x, z, elevval, 'Sand', bathyval, 'Water')
        elif (lcval == 12):
            # ice
            layers(x, z, elevval, 'Sand', bathyval, 'Ice')
        elif (lcval == 21):
            # developed/open-space (20% stone 80% grass rand tree)
            if (random() < 0.20):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 22):
            # developed/open-space (35% stone 65% grass rand tree)
            if (random() < 0.35):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 23):
            # developed/open-space (65% stone 35% grass rand tree)
            if (random() < 0.65):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 24):
            # developed/open-space (90% stone 10% grass rand tree)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 31):
            # barren land (baseline% sand baseline% stone)
            if (random() < 0.20):
                blockType = 'Stone'
            else:
                placeTree(x, z, elevval, treeProb, -1)
                blockType = 'Sand'
            layers(x, z, elevval, 'Sand', 2, blockType)
        elif (lcval == 32):
            # unconsolidated shore (sand)	 
            layers(x, z, elevval, 'Sand')
        elif (lcval == 41):
            # deciduous forest (grass with tree #1)
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, treeProb*5, 2)
        elif (lcval == 42):
            # evergreen forest (grass with tree #2)
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, treeProb*5, 1)
        elif (lcval == 43):
            # mixed forest (grass with either tree)
            if (random() < 0.50):
                treeType = 0
            else:
                treeType = 1
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, treeProb*5, treeType)
        elif (lcval == 51):
            # dwarf scrub (grass with 25% stone)
            if (random() < 0.25):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 52):
            # shrub/scrub (grass with 25% stone)
            # FIXME: make shrubs?
            if (random() < 0.25):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 71):
            # grasslands/herbaceous
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
        elif (lcval == 72):
            # sedge/herbaceous
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
        elif (lcval == 73):
            # lichens (90% stone 10% grass)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 74):
            # moss (90% stone 10% grass)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 81):
            # pasture/hay
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
        elif (lcval == 82):
            # cultivated crops
            layers(x, z, elevval, 'Dirt', 1, 'Grass')
        elif (lcval == 90):
            # woody wetlands (grass with rand trees and -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb*5, 1)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 91):
            # palustrine forested wetlands
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb*5, 0)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 92):
            # palustrine scrub/shrub wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 93):
            # estuarine forested wetlands (grass with rand trees and water)
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb*5, 2)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 94):
            # estuarine scrub/shrub wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 95):
            # emergent herbaceous wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Dirt', 1, blockType)
        elif (lcval == 96):
            # palustrine emergent wetlands-persistent (-1m water?)
            layers(x, z, elevval, 'Dirt', 1, 'Water')
        elif (lcval == 97):
            # estuarine emergent wetlands (-1m water)
            layers(x, z, elevval, 'Dirt', 1, 'Water')
        elif (lcval == 98):
            # palustrine aquatic bed (-1m water)
            layers(x, z, elevval, 'Dirt', 1, 'Water')
        elif (lcval == 99):
            # estuarine aquatic bed (-1m water)
            layers(x, z, elevval, 'Dirt', 1, 'Water')

# fills a column with layers of stuff
# examples:
# layers(x, y, elevval, 'Stone')
#  - fill everything from 0 to elevval with stone
# layers(x, y, elevval, 'Dirt', 2, 'Water')
#  - elevval down two levels of water, rest dirt
# layers(x, y, elevval, 'Stone', 1, 'Dirt', 1, 'Water')
#  - elevval down one level of water, then one level of dirt, then stone
def layers(x, z, elevval, *args):
    global level
    bottom = sealevel
    top = sealevel+elevval

    [setBlockAt(x, y, z, 'Stone') for y in xrange(0,bottom)]
    data = list(args)
    while (len(data) > 0 or bottom < top):
        # better be a block
        block = data.pop()
        #print 'block is %s' % block
        if (len(data) > 0):
            layer = data.pop()
        else:
            layer = top - bottom
        # now do something
        #print 'layer is %d' % layer
        if (layer > 0):
           [setBlockAt(x, y, z, block) for y in xrange(top-layer,top)]
           top -= layer
        
# places leaves and tree
def makeTree(x, z, elevval, height, treeType):
    global level
    global treeTotal
    #print 'makeTree @ (%d, %d, %d) - %d' % (x, z, elevval, clock()-starttime)
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
                            deltax = math.fabs(xindex-x)
                            deltaz = math.fabs(zindex-z)
                            sumsquares = math.pow(deltax,2)+math.pow(deltaz,2)
                            if (math.sqrt(sumsquares) < curleafwidth*.75):
                                setBlockAt(xindex, y, zindex, 'Leaves')
                                setBlockDataAt(xindex, y, zindex, treeType)
                if (index < height):
                    setBlockAt(x, y, z, 'Wood')
                    setBlockDataAt(x, y, z, treeType)
                
    # increment tree count
    treeCount[treeType+1] += 1
    treeTotal += 1

def placeTree(x, z, elevval, prob, treeType):
    chance = random()
    if (chance < prob):
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

# my own setblockat
def setBlockAt(x, y, z, string):
    global level
    blockType = level.materials.materialNamed(string)
    try:
        level.setBlockAt(x, y, z, blockType)
    except mclevel.ChunkNotPresent as inst:
        level.createChunk(inst[0], inst[1])
        level.setBlockAt(x, y, z, blockType)

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global level
    try:
        level.setBlockDataAt(x, y, z, data)
    except mclevel.ChunkNotPresent as inst:
        level.createChunk(inst[0], inst[1])
        level.setBlockDataAt(x, y, z, data)

# everything an explorer needs, for now
def equipPlayer():
    global level
    # eventually give out full iron toolset and a handful of torches
    inventory = level.root_tag['Data']['Player']['Inventory']
    inventory.append(Itemstack(278, slot=8))
    inventory.append(Itemstack(50, slot=0, count=-1)) # Torches
    inventory.append(Itemstack(1, slot=1, count=-1))  # Stone
    inventory.append(Itemstack(3, slot=2, count=-1))  # Dirt
    inventory.append(Itemstack(345, slot=35, count=1))  # Compass

def printLandCoverStatistics():
    print 'Land cover statistics (%d total):' % lcTotal
    lcTuples = [(lcType[index], lcCount[index]) for index in lcCount if lcCount[index] > 0]
    for key, value in sorted(lcTuples, key=lambda lc: lc[1], reverse=True):
        lcPercent = round((value*10000)/lcTotal)/100.0
        print '  %d (%f): %s' % (value, lcPercent, key)
    print 'Tree statistics (%d total):' % treeTotal
    treeTuples = [(treeType[index], treeCount[index]) for index in treeCount if treeCount[index] > 0]
    for key, value in sorted(treeTuples, key=lambda tree: tree[1], reverse=True):
        treePercent = round((value*10000)/treeTotal)/100.0
        print '  %d (%f): %s' % (value, treePercent, key)


def main(argv):
    global level

    # what region are we doing?
    region = 'BlockIsland'
    # what world are we doing?
    level = mclevel.MCInfdevOldLevel('/home/jmt/.minecraft/saves/World5', create=True)
    # FIXME: these should have defaults to "all files" eventually
    minrows = 0
    mincols = 0
    maxrows = 1520
    maxcols = 1990
    # maxrows = 2167
    # maxcols = 2140
    #maxrows = 1535
    #maxcols = 1535
    # tiling constants - also hopefully eventually optional
    tilerows = 256
    tilecols = 256

    # what are we doing?
    print 'Creating world from region %s' % region

    # initialize the land cover variables
    populateLandCoverVariables(lcType, lcCount, treeType, treeCount)

    # for loop time!
    # first make sure that minrows and mincols start on tile boundaries
    minrows -= (minrows % tilerows)
    mincols -= (mincols % tilecols)
    # for row in xrange(minrows, maxrows, tilerows):
    #     for col in xrange(mincols, maxcols, tilecols):
    #         processImage(row, col)
    pool = Pool(4)
    tasks = [(row, col) for row in xrange(minrows, maxrows, tilerows) for col in xrange(mincols, maxcols, tilecols)]
    results = pool.imap_unordered(processImagestar, tasks)
    bleah = [x for x in results]
                                    
    # maximum elevation
    print('Maximum elevation: %d' % maxelev)
    print('Maximum depth: %d' % maxbathy)

    # set player position and spawn point (in this case, equal)
    print 'Setting spawn values: %d, %d, %d' % (spawnx, (sealevel+spawny+2), spawnz)
    #equipPlayer()
    level.setPlayerPosition((spawnx, sealevel+spawny+2, spawnz))
    level.setPlayerSpawnPosition((spawnx, sealevel+spawny+2, spawnz))
    level.saveInPlace()
    print level.playerSpawnPosition()

    print 'Processing done -- took %f seconds.' % (clock()-starttime)
    printLandCoverStatistics()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
