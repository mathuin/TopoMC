# methods which manipulate arrays and their elements
import os
import shutil
import numpy
import multinumpy
import cPickle as pickle
from pymclevel import mclevel
from pymclevel.materials import alphaMaterials
from itertools import product
from multiprocessing import Pool
from memoize import memoize
from random import randint
import logging
logging.basicConfig(level=logging.WARNING)
mcarraylogger = logging.getLogger('mcarray')

# level constants
chunkWidthPow = 4
chunkWidth = pow(2,chunkWidthPow)
chunkHeight = 128
# constants
# headroom is the room between the tallest peak and the ceiling
headroom = 10
# use numpy savez/load routines
useNumpy = True

# level variables
minX = 0
minZ = 0
maxX = 0
maxZ = 0
maxcz = 0 # rotation
processes = 0
sealevel = 32 # this is now changed in BuildWorld.py
maxelev = chunkHeight-headroom-sealevel
arrayBlocks = {}
arrayData = {}

# check function
def checkSealevel(string):
    "Checks to see if the given sealevel is valid."
    # sea level can be between 2 and 100 (arbitrary, but so what)
    sealevel = max(min(string, 100), 1)
    if (sealevel != string):
        mcarraylogger.warning("Sealevel of %d is invalid -- changed to %d" % (string, sealevel))
    return sealevel

# helper functions for pymclevel
@memoize()
def materialNamed(string):
    "Returns block ID for block with name given in string."
    return [v.ID for v in alphaMaterials.allBlocks if v.name==string][0]

@memoize()
def names(blockID):
    "Returns block name for given block ID."
    return alphaMaterials.names[blockID][0]

def createArrays(aminX, aminZ, amaxX, amaxZ, asealevel, aprocesses):
    "Create shared arrays."
    global minX, minZ, maxX, maxZ, sealevel, processes, maxelev, maxcz, arrayBlocks, arrayData
    # assign level variables
    minX = aminX
    minZ = aminZ
    maxX = amaxX
    maxZ = amaxZ
    sealevel = asealevel
    processes = aprocesses
    # recalculate this based on new sealevel
    maxelev = chunkHeight-headroom-sealevel
    # calculate maxcz for rotation
    maxcz = (amaxX-aminX) >> chunkWidthPow
    # start creating arrays
    minXchunk = (minX >> chunkWidthPow)
    minZchunk = (minZ >> chunkWidthPow)
    maxXchunk = (maxX >> chunkWidthPow)
    maxZchunk = (maxZ >> chunkWidthPow)
    chunkX = xrange(minXchunk, maxXchunk+1)
    chunkZ = xrange(minZchunk, maxZchunk+1)
    for x, z in product(chunkX, chunkZ):
        arrayKey = '%dx%d' % (x, z)
        arrayBlocks[arrayKey] = multinumpy.SharedMemArray(numpy.zeros((chunkWidth,chunkWidth,chunkHeight),dtype=numpy.uint8))
        arrayData[arrayKey] = multinumpy.SharedMemArray(numpy.zeros((chunkWidth,chunkWidth,chunkHeight),dtype=numpy.uint8))

def saveArray(arraydir, key):
    "Save a particular array based on its key."
    global arrayBlocks, arrayData
    ctuple = key.split('x')
    ocx = int(ctuple[0])
    ocz = int(ctuple[1])
    cz = maxcz-ocx
    cx = ocz
    myBlocks = arrayBlocks[key].asarray()
    myData = arrayData[key].asarray()
    # save them to a file
    outfile = os.path.join(arraydir, '%dx%d' % (cx, cz))
    if (useNumpy):
        numpy.savez(outfile, blocks=myBlocks, data=myData)
    else:
        myCuke = {'blocks': myBlocks, 'data': myData}
        fd = open(outfile, 'wb')
        pickle.dump(myCuke, fd)
        fd.close()
    arrayBlocks[key] = None
    arrayData[key] = None

def saveArraystar(args):
    return saveArray(*args)

def saveArrays(arraydir, processes):
    "Save shared arrays."
    # make arraydir
    if os.path.isdir(arraydir):
        shutil.rmtree(arraydir)
    if not os.path.exists(arraydir):
        os.makedirs(arraydir)
    else:
        raise IOError, "%s already exists" % arraydir
    # distribute this
    # FIXME: numpy.savez is not threadsafe, sigh!
    if (processes == 1):
        arrays = [saveArray(arraydir, key) for key in arrayBlocks.keys()]
    else:
        pool = Pool(processes)
        tasks = [(arraydir, key) for key in arrayBlocks.keys()]
        results = pool.imap_unordered(saveArraystar, tasks)
        arrays = [x for x in results]
        pool = None

def loadArray(world, arraydir, name):
    "Load array from file."
    # extract arrays from file
    fd = open(os.path.join(arraydir,name), 'rb')
    if (useNumpy):
        infile = numpy.load(fd,mmap_mode=None)
        myBlocks = numpy.copy(infile['blocks'])
        myData = numpy.copy(infile['data'])
        infile = None
    else:
        myCuke = pickle.load(fd)
        myBlocks = numpy.copy(myCuke['blocks'])
        myData = numpy.copy(myCuke['data'])
        myCuke = None
    fd.close()
    # extract key from filename
    key = name.split('.')[0]
    ctuple = key.split('x')
    cx = int(ctuple[0])
    cz = int(ctuple[1])
    try:
        world.getChunk(cx, cz)
    except mclevel.ChunkNotPresent:
        world.createChunk(cx, cz)
    chunk = world.getChunk(cx, cz)
    for x, z in product(xrange(chunkWidth), xrange(chunkWidth)):
        chunk.Blocks[x,z] = myBlocks[chunkWidth-1-z,x]
        chunk.Data[x,z] = myData[chunkWidth-1-z,x]
    chunk.chunkChanged()

def loadArraystar(args):
    return loadArray(*args)

def loadArrays(world, arraydir, processes):
    "Load all arrays from array directory."
    # FIXME: something about getChunk and friends isn't parallel-friendly
    if (processes == 1 or True):
        arrays = [loadArray(world, arraydir, name) for name in os.listdir(arraydir)]
    else:
        pool = Pool(processes)
        tasks = [(world, arraydir, name) for name in os.listdir(arraydir)]
        results = pool.imap_unordered(loadArraystar, tasks)
        arrays = [x for x in results]
        pool = None
    mcarraylogger.info('%d arrays loaded' % len(arrays))

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
        overstone = sum([column[elem] for elem in xrange(len(column)) if elem % 2 == 0])
        column.insert(0, 'Bedrock')
        column.insert(1, top-overstone-1)
        column.insert(2, 'Stone')
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
        value = materialNamed(string)
    except IndexError:
        mcarraylogger.warning("unknown block value: %s" % string)
        # set value to air
        value = 0
    try:
        myBlocks = arrayBlocks[arrayKey].asarray()
    except KeyError:
        mcarraylogger.warning("attempted to set block out of range: (%d, %d, %d, %s)" % (x, y, z, string))
    else:
        myBlocks[x & chunkWidth-1, z & chunkWidth-1, y] = value

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
    try:
        myData = arrayData[arrayKey].asarray()
    except KeyError:
        mcarraylogger.warning("attempted to set block out of range: (%d, %d, %d, %d)" % (x, y, z, data))
    else:
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
    try:
        myBlocks = arrayBlocks[arrayKey].asarray()
    except KeyError:
        mcarraylogger.warning("attempted to get block out of range: (%d, %d, %d, %s)" % (x, y, z, string))
        return names(0)
    else:
        myBlock = myBlocks[x & chunkWidth-1, z & chunkWidth-1, y]
    try:
        names(myBlock)
    except IndexError:
        mcarraylogger.warning("unknown block value: %s" % myBlock)
        return 0
    else:
        return names(myBlock)
    
def getBlockDataAt(x, y, z):
    "Returns the data value of the block at this point."
    arrayKey = '%dx%d' % (x >> chunkWidthPow, z >> chunkWidthPow)
    try:
        myData = arrayData[arrayKey].asarray()
    except KeyError:
        mcarraylogger.warning("attempted to get block out of range: (%d, %d, %d, %d)" % (x, y, z, data))
        return 0
    else:
        return myData[x & chunkWidth-1, z & chunkWidth-1, y]

def getBlocksAt(blocks):
    "Returns the block names of the blocks in the list."
    retval = []
    for block in blocks:
        (x, y, z) = block
        retval.append(getBlockAt(x, y, z))
    return retval
