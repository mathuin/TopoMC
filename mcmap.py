# minecraft map module
from numpy import empty, uint8, copy
from pymclevel import mclevel
from pymclevel.materials import materials
from pymclevel.box import BoundingBox
from time import clock
from multiprocessing import Pool

# constants
sealevel = 64
headroom = 5
maxelev = 128-sealevel-headroom

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
        arrayBlocks[arrayKey] = empty((16,16,128))
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
        arrayData[arrayKey] = empty((16,16,128))
    arrayData[arrayKey][ix,iz,y] = data

def populateChunk(key):
    #print "key is %s" % (key)
    global world
    start = clock()
    ctuple = key.split(',')
    cx = int(ctuple[0])
    cz = int(ctuple[1])
    try:
        world.getChunk(cx, cz)
    except mclevel.ChunkNotPresent:
        world.createChunk(cx, cz)
    chunk = world.getChunk(cx, cz)
    chunk.Blocks[:,:,:] = arrayBlocks[key][:,:,:]
    arrayBlocks[key] = None
    if key in arrayData:
        chunk.Data[:,:,:] = arrayData[key][:,:,:]
        arrayData[key] = None
    chunk.chunkChanged()
    return (clock()-start)

def populateChunkstar(args):
    return populateChunk(*args)

def populateWorld(processes):
    global world
    if (processes == 1):
        times = [populateChunk(key,) for key in arrayBlocks.keys()]
    else:
        pool = Pool(processes)
        tasks = [(key,) for key in arrayBlocks.keys()]
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

def saveWorld(peak):
    global world
    # incoming peak is in xzy
    peakxyz = (peak[0], peak[2]+sealevel+2, peak[1])
    world.setPlayerPosition(peakxyz)
    world.setPlayerSpawnPosition(peakxyz)
    world.generateLights()
    world.saveInPlace()

# variables
arrayBlocks = {}
arrayData = {}

