# minecraft map module
from numpy import empty, empty_like, uint8
from pymclevel import mclevel
from pymclevel.box import BoundingBox
import image

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
    blockType = world.materials.materialNamed(string)
    arrayBlocks[x,z,y] = blockType

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global arrayData
    arrayData[x,z,y] = data

def populateChunk(region, chunk):
    global world
    (size_z, size_x) = image.imageDims[region]
    (cx, cz) = chunk.chunkPosition
    newminx = cx * 16
    newminz = cz * 16
    for z in xrange(min(16,size_z-newminz)):
        for x in xrange(min(16,size_x-newminx)):
            chunk.Blocks[x,z] = arrayBlocks[newminx+x,newminz+z]
            chunk.Data[x,z] = arrayData[newminx+x,newminz+z]
    chunk.chunkChanged()
    
def createArrays(region):
    global arrayBlocks
    global arrayData
    "Create arrays used by blocks based on dimensions."
    (size_z, size_x) = image.imageDims[region]
    arrayBlocks = empty([size_x+1, size_z+1, 128],dtype=uint8)
    arrayData = empty_like(arrayBlocks)
    return arrayBlocks, arrayData

def initializeWorld(worldNum):
    global world
    "Create a new Minecraft world given a value."
    # FIXME: bogus!
    filename = "/home/jmt/.minecraft/saves/World%d" % worldNum
    world = mclevel.MCInfdevOldLevel(filename, create = True);
    world.createChunksInBox(BoundingBox((0,0,0),(arrayBlocks.shape[0], 128, arrayBlocks.shape[1])))
    return world

def saveWorld(peak):
    global world
    world.setPlayerPosition(peak)
    world.setPlayerSpawnPosition(peak)
    world.generateLights()
    world.saveInPlace()
