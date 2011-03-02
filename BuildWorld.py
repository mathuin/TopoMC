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
import ore
import dataset
import os

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
    # FIXME
    parser = argparse.ArgumentParser(description='Generate Minecraft worlds from images based on USGS datasets.')
    parser.add_argument('--region', nargs='?', type=dataset.checkDataset, help='a region to be processed (leave blank for list of regions)')

    # this is global
    args = parser.parse_args()

    # what are we doing?
    print 'Creating world from region %s' % args.region

    # create shared memory for each expected chunk
    worlddir = os.path.join("Worlds", args.region)
    mcmap.myinitWorld(worlddir)

    # load arrays
    arraydir = os.path.join("Arrays", args.region)
    mcmap.loadArrays(arraydir)

    # save world
    mcmap.mysaveWorld()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
