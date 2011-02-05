# minecraft map module
from numpy import empty, array, uint8, zeros
from pymclevel import mclevel
from pymclevel.materials import materials
from pymclevel.box import BoundingBox
from time import clock
from multiprocessing import Pool
from itertools import product

# constants
sealevel = 64
# headroom is the room between the tallest peak and the ceiling
headroom = 5
maxelev = 128-headroom-sealevel
rotateMe = True

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
        
# my own setblockat
def setBlockAt(x, y, z, string):
    global arrayBlocks
    blockType = materials.materialNamed(string)
    cx = x >> 4
    cz = z >> 4
    ix = x & 0xf
    iz = z & 0xf
    arrayKey = '%d,%d' % (cx,cz)
    try:
        arrayBlocks[arrayKey]
    except KeyError:
        arrayBlocks[arrayKey] = zeros((16,16,128),dtype=uint8)
    arrayBlocks[arrayKey][ix,iz,y] = blockType

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global arrayData
    cx = x >> 4
    cz = z >> 4
    ix = x & 0xf
    iz = z & 0xf
    arrayKey = '%d,%d' % (cx,cz)
    try:
        arrayData[arrayKey]
    except KeyError:
        arrayData[arrayKey] = zeros((16,16,128),dtype=uint8)
    arrayData[arrayKey][ix,iz,y] = data

def populateChunk(key,maxcz):
    #print "key is %s" % (key)
    global world
    start = clock()
    ctuple = key.split(',')
    # JMT: trying to fix rotated files
    ocx = int(ctuple[0])
    ocz = int(ctuple[1])
    if (rotateMe):
        cz = maxcz-ocx
        cx = ocz
    else:
        cz = ocz
        cx = ocx
    try:
        world.getChunk(cx, cz)
    except mclevel.ChunkNotPresent:
        world.createChunk(cx, cz)
    chunk = world.getChunk(cx, cz)
    world.compressChunk(cx, cz)
    if (rotateMe):
        if (True):
            for x, z in product(xrange(16), xrange(16)):
                chunk.Blocks[x,z] = arrayBlocks[key][15-z,x]
        else:
            for x, z, y in product(xrange(16), xrange(16), xrange(128)):
                chunk.Blocks[x,z,y] = arrayBlocks[key][15-z,x,y]
    else:
        chunk.Blocks[:,:,:] = arrayBlocks[key][:,:,:]
    arrayBlocks[key] = None
    if key in arrayData:
        if (rotateMe):
            if (True):
                for x, z in product(xrange(16), xrange(16)):
                    chunk.Data[x,z] = arrayData[key][15-z,x]
            else:
                for x, z, y in product(xrange(16), xrange(16), xrange(128)):
                    chunk.Data[x,z,y] = arrayData[key][15-z,x,y]
        else:
            chunk.Data[:,:,:] = arrayData[key][:,:,:]
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

def initializeWorld(worldNum):
    global world
    "Create a new Minecraft world given a value."
    # FIXME: bogus!
    filename = "/home/jmt/.minecraft/saves/World%d" % worldNum
    world = mclevel.MCInfdevOldLevel(filename, create = True);
    return world

def saveWorld(spawn):
    global world
    # incoming spawn is in xzy
    # adjust it to sealevel, and then up another two for good measure
    spawnxyz = (spawn[0], spawn[2]+sealevel+2, spawn[1])
    world.setPlayerPosition(spawnxyz)
    world.setPlayerSpawnPosition(spawnxyz)
    world.generateLights()
    world.saveInPlace()

# variables
arrayBlocks = {}
arrayData = {}

