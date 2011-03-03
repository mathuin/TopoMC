#!/usr/bin/env python

import sys
sys.path.append('..')
import argparse
from multiprocessing import cpu_count
#
import mcmap
import mcarray
import dataset
import os

def checkProcesses(args):
    "Checks to see if the given process count is valid."
    if (isinstance(args.processes, list)):
        processes = args.processes[0]
    else:
        processes = int(args.processes)
    args.processes = processes
    return processes

def main(argv):
    default_processes = cpu_count()
    parser = argparse.ArgumentParser(description='Generate Minecraft worlds from images based on USGS datasets.')
    parser.add_argument('--region', nargs='?', type=dataset.checkDataset, help='a region to be processed (leave blank for list of regions)')
    parser.add_argument('--processes', nargs=1, default=default_processes, type=int, help="number of processes to spawn (default %d)" % default_processes)

    # this is global
    args = parser.parse_args()
    processes = checkProcesses(args)

    # what are we doing?
    print 'Creating world from region %s' % args.region

    # create shared memory for each expected chunk
    worlddir = os.path.join("Worlds", args.region)
    mcmap.myinitWorld(worlddir)

    # load arrays
    arraydir = os.path.join("Arrays", args.region)
    mcarray.loadArrays(mcmap.world, arraydir, processes)

    # save world
    mcmap.mysaveWorld()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
