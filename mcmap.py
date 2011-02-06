# minecraft map module
import os
from numpy import empty, array, uint8, zeros
from pymclevel import mclevel
from pymclevel.materials import materials
from pymclevel.box import BoundingBox
from time import clock
from multiprocessing import Pool
from itertools import product
from random import randint

# constants
sealevel = 64
# headroom is the room between the tallest peak and the ceiling
headroom = 5
maxelev = 128-headroom-sealevel

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
    bottom = 0
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

def manylayers(columns):
    blocks = []
    for column in columns:
        x = column.pop(0)
        z = column.pop(0)
        elevval = column.pop(0)
        top = sealevel+elevval
        # gonna have to add 'Stone', randint(5,7) to args list somehow
        column.insert(0, 'Stone')
        column.insert(1, randint(5,7))
        while (len(column) > 0 or top > 0):
            # better be a block
            block = column.pop()
            # print 'block is %s' % block
            if (len(column) > 0):
                layer = column.pop()
            else:
                layer = top
            # now do something
            # print 'layer is %d' % layer
            if (layer > 0):
                (blocks.append((x, y, z, block)) for y in xrange(top-layer,top))
                top -= layer
    setBlocksAt(blocks)
        
# my own setblockat
def setBlockAt(x, y, z, string):
    global arrayBlocks
    arrayKey = '%d,%d' % (x >> 4, z >> 4)
    try:
        arrayBlocks[arrayKey]
    except KeyError:
        arrayBlocks[arrayKey] = zeros((16,16,128),dtype=uint8)
    arrayBlocks[arrayKey][x & 0xf, z & 0xf, y] = materials.materialNamed(string)

# more aggregates
def setBlocksAt(blocks):
    global arrayBlocks
    for block in blocks:
        (x, y, z, string) = block
        arrayKey = '%d,%d' % (x >> 4, z >> 4)
        try:
            arrayBlocks[arrayKey]
        except KeyError:
            arrayBlocks[arrayKey] = zeros((16,16,128),dtype=uint8)
        arrayBlocks[arrayKey][x & 0xf, z & 0xf, y] = materials.materialNamed(string)

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global arrayData
    arrayKey = '%d,%d' % (x >> 4, z >> 4)
    try:
        arrayData[arrayKey]
    except KeyError:
        arrayData[arrayKey] = zeros((16,16,128),dtype=uint8)
    arrayData[arrayKey][x & 0xf, z & 0xf, y] = data

def populateChunk(key,maxcz):
    #print "key is %s" % (key)
    global world
    start = clock()
    ctuple = key.split(',')
    # JMT: trying to fix rotated files
    ocx = int(ctuple[0])
    ocz = int(ctuple[1])
    cz = maxcz-ocx
    cx = ocz
    try:
        world.getChunk(cx, cz)
    except mclevel.ChunkNotPresent:
        world.createChunk(cx, cz)
    chunk = world.getChunk(cx, cz)
    world.compressChunk(cx, cz)
    for x, z in product(xrange(16), xrange(16)):
        chunk.Blocks[x,z] = arrayBlocks[key][15-z,x]
    arrayBlocks[key] = None
    if key in arrayData:
        for x, z in product(xrange(16), xrange(16)):
            chunk.Data[x,z] = arrayData[key][15-z,x]
        arrayData[key] = None
    chunk.chunkChanged()
    return (clock()-start)

def populateChunkstar(args):
    return populateChunk(*args)

def populateWorld(processes):
    global world
    allkeys = array([list(key.split(',')) for key in arrayBlocks.keys()])
    maxcz = int(max(allkeys[:,1]))
    # FIXME: no multiprocessor support here either
    if (processes == 1 or True):
        times = [populateChunk(key,maxcz) for key in arrayBlocks.keys()]
    else:
        pool = Pool(processes)
        tasks = [(key,maxcz) for key in arrayBlocks.keys()]
        results = pool.imap_unordered(populateChunkstar, tasks)
        times = [x for x in results]
    count = len(times)
    print '%d chunks written (average time %.2f seconds)' % (count, sum(times)/count)

def checkWorld(string):
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
            #myworld = mclevel.loadWorldNumber(worldNum)
            string = worldNum
        else:
            raise IOError, "bad value for world: %s" % string
    return string

def initWorld(string):
    "Open this world."
    global world
    if string.isdigit():
        myworld = mclevel.loadWorldNumber(string)
    else:
        myworld = mclevel.fromFile(string)
    return myworld

def saveWorld(spawn):
    global world
    sizeOnDisk = 0
    # incoming spawn is in xzy
    # adjust it to sealevel, and then up another two for good measure
    spawnxyz = (spawn[0], spawn[2]+sealevel+2, spawn[1])
    world.setPlayerPosition(spawnxyz)
    world.setPlayerSpawnPosition(spawnxyz)
    world.generateLights()
    # stolen from pymclevel/mce.py
    for i, cPos in enumerate(world.allChunks, 1):
        ch = world.getChunk(*cPos);
        sizeOnDisk += ch.compressedSize();
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()

# variables
arrayBlocks = {}
arrayData = {}

