#!/usr/bin/env python

import sys
sys.path.append('..')
import argparse
from time import clock
from multiprocessing import cpu_count
#
import image
import terrain
import tree
import mcmap

# everything an explorer needs, for now
def equipPlayer():
    global args
    # eventually give out full iron toolset and a handful of torches
    inventory = args.world.root_tag['Data']['Player']['Inventory']
    inventory.append(Itemstack(278, slot=8))
    inventory.append(Itemstack(50, slot=0, count=-1)) # Torches
    inventory.append(Itemstack(1, slot=1, count=-1))  # Stone
    inventory.append(Itemstack(3, slot=2, count=-1))  # Dirt
    inventory.append(Itemstack(345, slot=35, count=1))  # Compass

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
    default_world = 5
    default_nodata = 11
    parser = argparse.ArgumentParser(description='Generate Minecraft worlds from images based on USGS datasets.')
    parser.add_argument('region', nargs='?', type=image.checkImageset, help='a region to be processed (leave blank for list of regions)')
    parser.add_argument('--processes', nargs=1, default=default_processes, type=int, help="number of processes to spawn (default %d)" % default_processes)
    parser.add_argument('--nodata', nargs=1, default=default_nodata, type=int, help="value to substitute when landcover file has no data (default %d)" % default_nodata)
    parser.add_argument('--world', default=default_world, type=mcmap.checkWorld, help="number of world to generate (default %d)" % default_world)

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

    # iterate over images
    peaks = image.processImages(args.region, args.processes)

    # per-tile peaks here
    # ... consider doing something nice on all the peaks?
    peak = sorted(peaks, key=lambda point: point[2], reverse=True)[0]

    # write array to level
    mcmap.populateWorld(args.processes)

    # maximum elevation
    print 'Maximum elevation: %d (at %d, %d)' % (peak[2], peak[0], peak[1])

    # set player position and spawn point (in this case, equal)
    #equipPlayer()
    mcmap.saveWorld(peak)

    print 'Processing done -- took %.2f seconds.' % (clock()-maintime)
    terrain.printLandCoverStatistics()
    tree.printTreeStatistics()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
