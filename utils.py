# utils module
import os, fnmatch
import shutil
from memoize import memoize
from pymclevel.materials import alphaMaterials
import numpy as np

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

# http://code.activestate.com/recipes/499305-locating-files-throughout-a-directory-tree/
def locate(pattern, root=os.curdir):
    '''Locate all files matching supplied filename pattern in and below supplied root directory.'''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)

def chunks(data, chunksize=100):
    """Overly-simple chunker..."""
    intervals = range(0, data.size, chunksize) + [None]
    for start, stop in zip(intervals[:-1], intervals[1:]):
        yield np.array(data[start:stop])

