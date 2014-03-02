# utils module
import os
import fnmatch
import shutil
from memoize import memoize
from pymclevel.materials import alphaMaterials
import numpy as np
from math import log


def cleanmkdir(dir):
    """Cleans out existing directory and rebuilds."""
    if os.path.isdir(dir):
        shutil.rmtree(dir)
    if not os.path.exists(dir):
        os.makedirs(dir)
    else:
        raise IOError('%s already exists' % dir)
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
        ch = world.getChunk(*cPos)
        numchunks += 1
        sizeOnDisk += ch.compressedSize()
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()


@memoize()
def materialNamed(string):
    "Returns block ID for block with name given in string."
    return [v.ID for v in alphaMaterials.allBlocks if v.name == string][0]


@memoize()
def names(blockID):
    "Returns block name for given block ID."
    return alphaMaterials.names[blockID][0]


def height(column):
    """Calculate the height of the column."""
    # NB: confirm that the column matches expectation
    if isinstance(column[0], tuple):
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


def build_tree(coords):
    """Build left-balanced KD tree from coordinates."""
    # initialize tree and stack
    tree = np.empty(len(coords)+1, dtype=np.uint32)
    tree[0] = 0
    stack = []

    # seed stack
    initial_indices = np.array([x for x in xrange(coords.shape[0])])
    initial_axis = 0
    initial_location = 1
    stack.append((initial_indices, initial_axis, initial_location))

    # work through stack
    while (len(stack) > 0):
        (indices, axis, location) = stack.pop()
        # if location is out of bounds, freak out
        if (location < 1 or location > len(tree)):
            raise IndexError('bad location: %d' % location)
        # if only one index, we are a leaf
        if (len(indices) == 1):
            tree[location] = indices[0]
            continue
        # generate sorted index of array
        splitarr = np.hsplit(coords[indices], 2)
        newindices = np.lexsort((splitarr[1-axis].ravel(), splitarr[axis].ravel()))
        # now calculate n, m, and r
        n = len(newindices)
        m = int(2**(int(log(n, 2))))
        r = n-(m-1)
        # median?
        if (r <= (m/2)):
            median = (m-2)/2+r+1
        else:
            median = (m-2)/2+m/2+1
        tree[location] = indices[newindices[median-1]]
        if (median > 0):
            stack.append((indices[newindices[:median-1]], 1-axis, location*2))
        if (median < len(indices)):
            stack.append((indices[newindices[median:]], 1-axis, location*2+1))

    # return the tree
    return tree
