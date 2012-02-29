# utils module
import os
import shutil
from memoize import memoize
import sys
sys.path.append('..')
from pymclevel.materials import alphaMaterials

def cleanmkdir(dir):
    """Cleans out existing directory and rebuilds."""
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    if not os.path.exists(dir):
        os.makedirs(dir)
    else:
        raise IOError, '%s already exists' % dir
    return dir

def setspawnandsave(world, point):
    """Sets the spawn point and player point in the world and saves the world."""
    world.setPlayerPosition(tuple(point))
    spawn = point
    spawn[1] += 2
    world.setPlayerSpawnPosition(tuple(spawn))
    sizeOnDisk = 0
    # NB: numchunks is calculable = (region.tilesize/chunkWidth)*(region.tilesize/chunkWidth)
    numchunks = 0
    for i, cPos in enumerate(world.allChunks, 1):
        ch = world.getChunk(*cPos);
        numchunks += 1
        sizeOnDisk += ch.compressedSize();
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()

@memoize()
def materialNamed(string):
    "Returns block ID for block with name given in string."
    return [v.ID for v in alphaMaterials.allBlocks if v.name==string][0]

@memoize()
def names(blockID):
    "Returns block name for given block ID."
    return alphaMaterials.names[blockID][0]

def height(column):
    """Calculate the height of the column."""
    # NB: confirm that the column matches expectation
    if type(column[0]) is tuple:
        pairs = column
    else:
        print "oops, missed one!"
        pairs = zip(column[::2], column[1::2])
    retval = sum([pair[0] for pair in pairs])
    return retval

