#!/usr/bin/env python

import sys
sys.path.append('..')
import argparse
from time import clock
from multiprocessing import cpu_count, RawArray
from itertools import product
from multinumpy import SharedMemArray
from numpy import zeros, uint8
from pymclevel import mclevel
from pymclevel.nbt import TAG_List, TAG_Compound, TAG_Short, TAG_Byte
#
import image
import terrain
import tree
import mcmap
import building

# everything an explorer needs, for now
def equipPlayer(world):
    # eventually give out full iron toolset and a handful of torches
    inventory = world.root_tag['Data']['Player']['Inventory']
    # Test object: compass
    mycompass = TAG_Compound()
    mycompass["Id"] = TAG_Short(345)
    mycompass["Damage"] = TAG_Short(0)
    mycompass["Count"] = TAG_Byte(1)
    mycompass["Slot"] = TAG_Byte(35)
    inventory.append(mycompass)
    
    # create a TAG_Compound object with the following values:
    # Id: <item or block id>
    # Damage: 0
    # Count: -1 seems to be infinite
    # Slot: where does it go

    #inventory.append(Itemstack(278, slot=8))
    #inventory.append(Itemstack(50, slot=0, count=-1)) # Torches
    #inventory.append(Itemstack(1, slot=1, count=-1))  # Stone
    #inventory.append(Itemstack(3, slot=2, count=-1))  # Dirt
    #inventory.append(Itemstack(345, slot=35, count=1))  # Compass

def checkProcesses(args):
    "Checks to see if the given process count is valid."
    if (isinstance(args.processes, list)):
        processes = args.processes[0]
    else:
        processes = int(args.processes)
    args.processes = processes
    return processes

def main(argv):
    maintime = clock()
    default_processes = cpu_count()
    default_nodata = 11
    parser = argparse.ArgumentParser(description='Generate Minecraft worlds from images based on USGS datasets.')
    parser.add_argument('--region', nargs='?', type=image.checkImageset, help='a region to be processed (leave blank for list of regions)')
    parser.add_argument('--processes', nargs=1, default=default_processes, type=int, help="number of processes to spawn (default %d)" % default_processes)
    parser.add_argument('--nodata', nargs=1, default=default_nodata, type=int, help="value to substitute when landcover file has no data (default %d)" % default_nodata)
    parser.add_argument('--world', type=mcmap.checkWorld, help="name or number of world to generate")

    # this is global
    args = parser.parse_args()

    # list regions if requested
    if (args.region == None):
        image.listImagesets()
        return 0

    # set up all the values
    processes = checkProcesses(args)
    terrain.nodata = args.nodata
    mcmap.world = mcmap.initWorld(args.world)
    
    # what are we doing?
    print 'Creating world from region %s' % args.region

    # create shared memory for each expected chunk
    maxX, maxZ = image.imageDims[args.region]
    maxXchunk = (maxX >> 4)
    maxZchunk = (maxZ >> 4)
    for x, z in product(xrange(-1,maxXchunk+1), xrange(-1,maxZchunk+1)):
        arrayKey = '%d,%d' % (x, z)
        try:
            mcmap.world.getChunk(z, x)
        except mclevel.ChunkNotPresent:
            mcmap.world.createChunk(z, x)
        mcmap.world.compressChunk(z, x)
        mcmap.arrayBlocks[arrayKey] = SharedMemArray(zeros((16,16,128),dtype=uint8))
        mcmap.arrayData[arrayKey] = SharedMemArray(zeros((16,16,128),dtype=uint8))

    # iterate over images
    peaks = image.processImages(args.region, args.processes)
        
    # per-tile peaks here
    # ... consider doing something nice on all the peaks?
    peak = sorted(peaks, key=lambda point: point[2], reverse=True)[0]

    # place the safehouse at the peak (adjust it)
    building.building(peak[0], peak[1], peak[2]-1, 7, 9, 8, 1)

    # write array to level
    mcmap.populateWorld(args.processes,maxXchunk)

    # maximum elevation
    print 'Maximum elevation: %d (at %d, %d)' % (peak[2], peak[0], peak[1])

    # set player position and spawn point (in this case, equal)
    equipPlayer(mcmap.world)
    mcmap.saveWorld(peak, maxX)

    print 'Processing done -- took %.2f seconds.' % (clock()-maintime)
    terrain.printLandCoverStatistics()
    tree.printTreeStatistics()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
