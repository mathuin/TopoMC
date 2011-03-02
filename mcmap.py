# minecraft map module
import os
import numpy
from pymclevel import mclevel
from pymclevel.materials import materials
from pymclevel.box import BoundingBox
from time import clock
from multiprocessing import Pool
from multinumpy import SharedMemArray
from numpy import zeros, uint8
from itertools import product
from random import randint

# level constants
chunkWidthPow = 4
chunkWidth = pow(2,chunkWidthPow)
chunkHeight = 128
# constants
sealevel = 64
# headroom is the room between the tallest peak and the ceiling
headroom = 10
maxelev = chunkHeight-headroom-sealevel

# variables
minX = 0
minZ = 0
maxX = 0
maxZ = 0
processes = 0

makeWorldNow = False

def myinitWorld(string):
    "Open this world."
    global world
    try:
        worldNum = int(string)
    except ValueError:
        world = mclevel.MCInfdevOldLevel(string, create=True)
    else:
        world = mclevel.loadWorldNumber(worldNum)

# each column consists of [x, z, elevval, ...]
# where ... is a block followed by zero or more number-block pairs
# examples:
# [x, y, elevval, 'Stone']
#  - fill everything from 0 to elevval with stone
# [x, y, elevval, 'Dirt', 2, 'Water']
#  - elevval down two levels of water, rest dirt
# [x, y, elevval, 'Stone', 1, 'Dirt', 1, 'Water']
#  - elevval down one level of water, then one level of dirt, then stone
# We add the final values here so the hard floor is 'Bedrock'.
def layers(columns):
    blocks = []
    for column in columns:
        x = column.pop(0)
        z = column.pop(0)
        elevval = column.pop(0)
        top = sealevel+elevval
        # overstone = sum([elem for elem in column if type(elem) == int])
        # column.insert(0, 'Bedrock')
        # column.insert(1, top-overstone-1)
        # column.insert(2, 'Stone')
        column.insert(0, 'Stone')
        while (len(column) > 0 or top > 0):
            # better be a block
            block = column.pop()
            if (len(column) > 0):
                layer = column.pop()
            else:
                layer = top
            # now do something
            if (layer > 0):
                [blocks.append((x, y, z, block)) for y in xrange(top-layer,top)]
                top -= layer
    setBlocksAt(blocks)
        
# fillBlocks(right, length, bottom, height, back, width, blockTypes.Air);
def fillBlocks(ix, dx, iy, dy, iz, dz, block, data=None):
    rx = xrange(int(ix), int(ix+dx))
    ry = xrange(int(iy), int(iy+dy))
    rz = xrange(int(iz), int(iz+dz))

    blockList = []
    dataList = []

    [blockList.append((x, y, z, block)) for x,y,z in product(rx, ry, rz)]
    setBlocksAt(blockList)

    if (data != None):
        [dataList.append((x, y, z, data)) for x,y,z in product(rx, ry, rz)]
        setBlocksDataAt(dataList)

# my own setblockat
def setBlockAt(x, y, z, string):
    global arrayBlocks
    arrayKey = '%dx%d' % (x >> chunkWidthPow, z >> chunkWidthPow)
    try:
        myBlocks = arrayBlocks[arrayKey].asarray()
    except KeyError:
        print "got key error with (%d, %d, %d, %s)" % (x, y, z, string)
        myBlocks = arrayBlocks[arrayKey].asarray()
    try:
        materials.materialNamed(string)
    except ValueError:
        print "got value error with (%d, %d, %d, %s)" % (x, y, z, string)
        materials.materialNamed(string)
    myBlocks[x & chunkWidth-1, z & chunkWidth-1, y] = materials.materialNamed(string)

# more aggregates
def setBlocksAt(blocks):
    global arrayBlocks
    for block in blocks:
        (x, y, z, string) = block
        setBlockAt(x, y, z, string)

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global arrayData
    arrayKey = '%dx%d' % (x >> chunkWidthPow, z >> chunkWidthPow)
    myData = arrayData[arrayKey].asarray()
    myData[x & chunkWidth-1, z & chunkWidth-1, y] = data

# my own setblocksdataat
def setBlocksDataAt(blocks):
    global arrayData
    for block in blocks:
        (x, y, z, data) = block
        setBlockDataAt(x, y, z, data)

def getBlockAt(x, y, z):
    "Returns the block ID of the block at this point."
    arrayKey = '%dx%d' % (x >> chunkWidthPow, z >> chunkWidthPow)
    myBlocks = arrayBlocks[arrayKey].asarray()
    return materials.names[myBlocks[x & chunkWidth-1, z & chunkWidth-1, y]]
    
def getBlockDataAt(x, y, z):
    "Returns the data value of the block at this point."
    arrayKey = '%dx%d' % (x >> chunkWidthPow, z >> chunkWidthPow)
    myData = arrayData[arrayKey].asarray()
    return myData[x & chunkWidth-1, z & chunkWidth-1, y]

def getBlocksAt(blocks):
    "Returns the block names of the blocks in the list."
    retval = []
    for block in blocks:
        (x, y, z) = block
        arrayKey = '%dx%d' % (x >> chunkWidthPow, z >> chunkWidthPow)
        myBlocks = arrayBlocks[arrayKey].asarray()
        retval.append(materials.names[myBlocks[x & chunkWidth-1, z & chunkWidth-1, y]])
    return retval

def populateChunk(key,maxcz):
    #print "key is %s" % (key)
    global world, arrayBlocks, arrayData
    start = clock()
    ctuple = key.split(',')
    ocx = int(ctuple[0])
    ocz = int(ctuple[1])
    cz = maxcz-ocx
    cx = ocz
    try:
        world.getChunk(cx, cz)
    except mclevel.ChunkNotPresent:
        world.createChunk(cx, cz)
    chunk = world.getChunk(cx, cz)
    #world.compressChunk(cx, cz)
    myBlocks = arrayBlocks[key].asarray()
    myData = arrayData[key].asarray()
    for x, z in product(xrange(chunkWidth), xrange(chunkWidth)):
        chunk.Blocks[x,z] = myBlocks[chunkWidth-1-z,x]
    arrayBlocks[key] = None
    myBlocks = None
    if key in arrayData:
        for x, z in product(xrange(chunkWidth), xrange(chunkWidth)):
            chunk.Data[x,z] = myData[chunkWidth-1-z,x]
    arrayData[key] = None
    myData = None
    chunk.chunkChanged(False)
    return (clock()-start)

def populateChunkstar(args):
    return populateChunk(*args)

def populateWorld():
    maxcx = (maxX-minX) >> chunkWidthPow
    # FIXME: still no multiprocessing support but less important
    if (processes == 1 or True):
        times = [populateChunk(key,maxcx) for key in arrayBlocks.keys()]
    else:
        pool = Pool(processes)
        tasks = [(key,maxcx) for key in arrayBlocks.keys()]
        results = pool.imap_unordered(populateChunkstar, tasks)
        times = [x for x in results]
    count = len(times)
    print '%d chunks written (average time %.2f seconds)' % (count, sum(times)/count)

def checkWorld(string):
    if (string == None):
        argparse.error("a world must be defined")
    try:
        worldNum = int(string)
    except ValueError:
        if not os.path.exists(string):
            os.mkdir(string)
        if not os.path.isdir(string):
            raise IOError, "%s already exists" % string
        level = mclevel.MCInfdevOldLevel(string, create=True)
        level.saveInPlace()
        level = None
        return string
    else:
        if 1 < worldNum <= 5:
            string = worldNum
        else:
            raise IOError, "bad value for world: %s" % string
    return string

def mysaveWorld():
    global world
    sizeOnDisk = 0
    # stolen from pymclevel/mce.py
    numchunks = 0
    for i, cPos in enumerate(world.allChunks, 1):
        ch = world.getChunk(*cPos);
        numchunks += 1
        sizeOnDisk += ch.compressedSize();
    print '%d chunks enumerated' % numchunks
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()

