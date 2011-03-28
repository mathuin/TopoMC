# minecraft world

import os
from pymclevel import mclevel

world = None

def myinitWorld(string):
    "Open this world."
    global world
    # it's a simpler universe now
    worlddir = os.path.join("Worlds", string)
    if not os.path.exists(worlddir):
        os.mkdir(worlddir)
    if not os.path.isdir(worlddir):
        raise IOError, "%s already exists" % worlddir
    world = mclevel.MCInfdevOldLevel(worlddir, create=True)

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

