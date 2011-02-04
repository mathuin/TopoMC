#!/usr/bin/env python

import sys
sys.path.append('..')
import re
import os
import argparse
from pymclevel import mclevel
from time import clock
from shutil import rmtree
import Image
import numpy
import math
from pymclevel.box import BoundingBox
from pymclevel.materials import materials
from random import random, randint
from multiprocessing import Pool, cpu_count

# paths for images
imagesPaths = ['Images']

# functions
def getImagesDict(imagepaths):
    "Given a list of paths, generate a dict of imagesets."
    # FIXME: check to see that images are 'complete' and report back sizes.
    # i.e., check names and dimensions

    imagere = re.compile(r'^(\w+)-(\d+)-(\d+).gif')

    imagedirs = {}
    imagesets = {}
    imagedims = {}
    for imagepath in imagepaths:
        regions = [ name for name in os.listdir(imagepath) if os.path.isdir(os.path.join(imagepath, name)) ]
        for region in regions:
            tmpis = {'lc': [], 'elev': [], 'bathy': []}
            imageregion = os.path.join(imagepath, region)
            for imagefile in os.listdir(imageregion):
                (filetype, offset_x, offset_z) = imagere.search(imagefile).groups()
                if (filetype in tmpis.keys()):
                    img = Image.open(os.path.join(imageregion, imagefile))
                    ary = numpy.asarray(img)
                    (size_x, size_z) = ary.shape
                    img = None
                    ary = None
                    tmpis[filetype].append(((int(offset_z), int(offset_x)), (int(size_x), int(size_z))))
            # lazy man will look for largest file and add the coordinates
            tmpid = {'lc': [], 'elev': [], 'bathy': []}
            for key in tmpid.keys():
                bigcorner = [0, 0]
                bigplus = [0, 0]
                for elem in tmpis[key]:
                    if (bigcorner[0] <= elem[0][0] and 
                        bigcorner[1] <= elem[0][1]):
                        bigcorner[0] = elem[0][0]
                        bigcorner[1] = elem[0][1]
                        bigplus[0] = elem[1][0]
                        bigplus[1] = elem[1][1]
                tmpid[key] = (bigcorner[0]+bigplus[0], bigcorner[1]+bigplus[1])
            if (set(tmpis['lc']) == set(tmpis['elev']) and 
                set(tmpis['lc']) == set(tmpis['bathy']) and 
                set(tmpid['lc']) == set(tmpid['elev']) and 
                set(tmpid['lc']) == set(tmpid['bathy'])):
                imagedirs[region] = os.path.join(imagepath, region)
                imagesets[region] = tmpis['lc']
                imagedims[region] = tmpid['lc']

    return imagedirs, imagesets, imagedims

# constants
sealevel = 64
baseline = 32 # below here is just stone
filler = sealevel - baseline

# set maxMapHeight to a conservative value
maxMapHeight = 125 - sealevel

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
def processImage(offset_z, offset_x):
    imagetime = clock()

    imgtemp = '%s/%%s-%d-%d.gif' % (imageDirs[mainargs.region], offset_x, offset_z)
    lcimg = Image.open(imgtemp % 'lc')
    elevimg = Image.open(imgtemp % 'elev')
    bathyimg = Image.open(imgtemp % 'bathy')

    lcarray = numpy.asarray(lcimg)
    elevarray = numpy.asarray(elevimg)
    bathyarray = numpy.asarray(bathyimg)

    # gotta start somewhere!
    localmax = 0
    spawnx = 10
    spawnz = 10

    # inform the user
    print 'Processing tile at position (%d, %d)...' % (offset_x, offset_z)
    (size_z, size_x) = lcarray.shape

    # iterate over the image
    for x in xrange(size_x):
        for z in xrange(size_z):
            lcval = lcarray[z][x]
            elevval = elevarray[z][x]
            bathyval = bathyarray[z][x]
            real_x = offset_x + x
            real_z = offset_z + z
            if (elevval > maxMapHeight):
                print('oh no elevation %d is too high' % elevval)
                elevval = maxMapHeight
            if (elevval > localmax):
                localmax = elevval
                spawnx = real_x
                spawnz = real_z
            processLcval(lcval, real_x, real_z, elevval, bathyval)
	
    # print out status
    print '... finished in %.2f seconds.' % (clock()-imagetime)

    return (spawnx, spawnz, localmax)

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
    global lcCount
    lcTotal += 1
    if (lcval not in lcType):
        print('unexpected value for land cover: ' + lcval)
        lcCount[0] += 1
        layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt')
    else:
        lcCount[lcval] += 1
        # http://www.mrlc.gov/nlcd_definitions.php
        if (lcval == 11):
            # water
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand', bathyval, 'Water')
        elif (lcval == 12):
            # ice
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand', bathyval, 'Ice')
        elif (lcval == 21):
            # developed/open-space (20% stone 80% grass rand tree)
            if (random() < 0.20):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 22):
            # developed/open-space (35% stone 65% grass rand tree)
            if (random() < 0.35):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 23):
            # developed/open-space (65% stone 35% grass rand tree)
            if (random() < 0.65):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 24):
            # developed/open-space (90% stone 10% grass rand tree)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 31):
            # barren land (baseline% sand baseline% stone)
            if (random() < 0.20):
                blockType = 'Stone'
            else:
                placeTree(x, z, elevval, treeProb, -1)
                blockType = 'Sand'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand', 2, blockType)
        elif (lcval == 32):
            # unconsolidated shore (sand)	 
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand')
        elif (lcval == 41):
            # deciduous forest (grass with tree #1)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, treeProb*5, 2)
        elif (lcval == 42):
            # evergreen forest (grass with tree #2)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, treeProb*5, 1)
        elif (lcval == 43):
            # mixed forest (grass with either tree)
            if (random() < 0.50):
                treeType = 0
            else:
                treeType = 1
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, treeProb*5, treeType)
        elif (lcval == 51):
            # dwarf scrub (grass with 25% stone)
            if (random() < 0.25):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 52):
            # shrub/scrub (grass with 25% stone)
            # FIXME: make shrubs?
            if (random() < 0.25):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 71):
            # grasslands/herbaceous
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 72):
            # sedge/herbaceous
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 73):
            # lichens (90% stone 10% grass)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 74):
            # moss (90% stone 10% grass)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 81):
            # pasture/hay
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 82):
            # cultivated crops
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 90):
            # woody wetlands (grass with rand trees and -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb*5, 1)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 91):
            # palustrine forested wetlands
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb*5, 0)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 92):
            # palustrine scrub/shrub wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 93):
            # estuarine forested wetlands (grass with rand trees and water)
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, treeProb*5, 2)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 94):
            # estuarine scrub/shrub wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 95):
            # emergent herbaceous wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 96):
            # palustrine emergent wetlands-persistent (-1m water?)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')
        elif (lcval == 97):
            # estuarine emergent wetlands (-1m water)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')
        elif (lcval == 98):
            # palustrine aquatic bed (-1m water)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')
        elif (lcval == 99):
            # estuarine aquatic bed (-1m water)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')

# fills a column with layers of stuff
# examples:
# layers(x, y, elevval, 'Stone')
#  - fill everything from 0 to elevval with stone
# layers(x, y, elevval, 'Dirt', 2, 'Water')
#  - elevval down two levels of water, rest dirt
# layers(x, y, elevval, 'Stone', 1, 'Dirt', 1, 'Water')
#  - elevval down one level of water, then one level of dirt, then stone
def layers(x, z, elevval, *args):
    global mainargs
    bottom = sealevel
    top = sealevel+elevval

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
    global mainargs
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
    # trees can't be too close to the edge
    treeDim = 10
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
        #temporarily disabling trees
        #makeTree(x, z, elevval, height, treeType)

# my own setblockat
def setBlockAt(x, y, z, string):
    global massarray
    blockType = materials.materialNamed(string)
    massarray[x,z,y] = blockType

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global massarraydata
    massarraydata[x,z,y] = data

# everything an explorer needs, for now
def equipPlayer():
    global mainargs
    # eventually give out full iron toolset and a handful of torches
    inventory = world.root_tag['Data']['Player']['Inventory']
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
        print '  %d (%.2f): %s' % (value, lcPercent, key)
    print 'Tree statistics (%d total):' % treeTotal
    treeTuples = [(treeType[index], treeCount[index]) for index in treeCount if treeCount[index] > 0]
    for key, value in sorted(treeTuples, key=lambda tree: tree[1], reverse=True):
        treePercent = round((value*10000)/treeTotal)/100.0
        print '  %d (%.2f): %s' % (value, treePercent, key)

def runThem(function, tasks, flag=False):
    if (mainargs.processes == 1 or flag == True):
        retval = [function(args) for args in tasks]
    else:
        pool = Pool(mainargs.processes)
        results = pool.imap_unordered(function, tasks)
        retval = [x for x in results]
    return retval

def listImagesets(imageDirs):
    "Given an images dict, list the imagesets and their dimensions."
    print 'Valid imagesets detected:'
    print "\n".join(["\t%s:\n\t\t%d tiles (%d, %d)" % (region, len(imageSets[region]), imageDims[region][0], imageDims[region][1]) for region in imageDirs])

def checkImageset(string):
    "Checks to see if there are images for this imageset."
    if (string != None and not string in imageDirs):
        listImagesets(imageDirs)
        argparse.error("%s is not a valid imageset" % string)
    return string

def checkProcesses(mainargs):
    "Checks to see if the given process count is valid."
    if (isinstance(mainargs.processes, list)):
        processes = mainargs.processes[0]
    else:
        processes = int(mainargs.processes)
    mainargs.processes = processes
    return processes

def populateChunk(args):
    (size_z, size_x) = imageDims[mainargs.region]
    (chunk, slices, point) = args
    (slicex, slicez, slicey) = slices
    (newminx, newminy, newminz) = point
    cx, cz = chunk.chunkPosition
    for z in xrange(min(16,size_z-newminz)):
        for x in xrange(min(16,size_x-newminx)):
            chunk.Blocks[x,z] = massarray[newminx+x,newminz+z]
            chunk.Data[x,z] = massarraydata[newminx+x,newminz+z]
    chunk.chunkChanged()
    
def main(argv):
    global mainargs
    global massarray
    global massarraydata
    global world
    maintime = clock()
    default_processes = cpu_count()
    default_world = 5
    parser = argparse.ArgumentParser(description='Generate Minecraft worlds from images based on USGS datasets.')
    parser.add_argument('region', nargs='?', type=checkImageset, help='a region to be processed (leave blank for list of regions)')
    parser.add_argument('--processes', nargs=1, default=default_processes, type=int, help="number of processes to spawn (default %d)" % default_processes)
    parser.add_argument('--world', default=default_world, type=int, choices=xrange(1,6), help="number of world to generate (default %d)" % default_world)

    # this is global
    mainargs = parser.parse_args()

    # list regions if requested
    if (mainargs.region == None):
        listImagesets(imageDirs)
        return 0

    # what are we doing?
    print 'Creating world from region %s' % mainargs.region

    # initialize the land cover variables
    populateLandCoverVariables(lcType, lcCount, treeType, treeCount)

    # set up all the values
    processes = checkProcesses(mainargs)
    
    # let us create massarray
    (size_z, size_x) = imageDims[mainargs.region]
    # yes, x z y
    massarray = numpy.empty([size_x, size_z, 128],dtype=numpy.uint8)
    massarraydata = numpy.empty_like(massarray)

    # opening the world
    #worlddir = "/home/jmt/.minecraft/saves/World%d" % mainargs.world
    #rmtree(worlddir)
    #os.mkdir(worlddir)
    world = mclevel.MCInfdevOldLevel(worlddir)

    # iterate over images
    # FIXME: this does not run in multiprocessor mode
    #peaks = runThem(processImagestar, ((offset[0], offset[1]) for (offset, size) in imageSets[mainargs.region]))
    peaks = [processImage(*offset) for (offset, size) in imageSets[mainargs.region]]

    # per-tile peaks here
    # ... consider doing something nice on all the peaks?
    peak = sorted(peaks, key=lambda point: point[2], reverse=True)[0]

    # write array to level
    # resetting the world
    for ch in list(world.allChunks):
        world.deleteChunk(*ch)
    world.createChunksInBox(BoundingBox((0,0,0), (size_x, 0, size_z)))
    times = [populateChunk(args) for args in world.getAllChunkSlices()]

    # maximum elevation
    print 'Maximum elevation: %d (at %d, %d)' % (peak[2], peak[0], peak[1])

    # set player position and spawn point (in this case, equal)
    #equipPlayer()
    world.setPlayerPosition(peak)
    world.setPlayerSpawnPosition(peak)
    world.generateLights()
    world.saveInPlace()

    print 'Processing done -- took %.2f seconds.' % (clock()-maintime)
    printLandCoverStatistics()

if __name__ == '__main__':
    imageDirs, imageSets, imageDims = getImagesDict(imagesPaths)
    sys.exit(main(sys.argv))
