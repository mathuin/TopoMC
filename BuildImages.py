#!/usr/bin/env python
# BuildImages.py - 2010Jan21 - mathuin@gmail.com
# part of TopoMC (https://github.com/mathuin/TopoMC)

# this script builds arrays for land cover and elevation

from __future__ import division
import sys
sys.path.append('..')
import os
import numpy
import Image
import argparse
from osgeo.gdal import UseExceptions
from osgeo import osr
from multiprocessing import Pool, cpu_count
from time import time
from random import random
from itertools import product
from invdisttree import *
from dataset import *
from coords import *
from tile import *
from bathy import *
from mcmap import maxelev
from crust import makeCrustIDT

def checkProcesses(args):
    "Checks to see if the given process count is valid."
    if (isinstance(args.processes, list)):
        processes = args.processes[0]
    else:
        processes = int(args.processes)
    args.processes = processes
    return processes

def checkScale(args):
    "Checks to see if the given scale is valid for the given region.  Returns scale and multiplier."
    fullScale = 1 # don't want higher resolution than reality!
    if (isinstance(args.scale, list)):
        oldscale = args.scale[0]
    else:
        oldscale = int(args.scale)
    lcds, elevds = getDataset(args.region)
    elevds = None
    lcperpixel = lcds.transforms[2][1]
    lcds = None
    scale = min(oldscale, lcperpixel)
    scale = max(scale, fullScale)
    if (scale != oldscale):
        print "Warning: scale of %d for region %s is invalid -- changed to %d" % (oldscale, args.region, scale)
    mult = lcperpixel/scale
    args.scale = scale
    args.mult = mult
    return (scale, mult)

def checkVScale(args):
    "Checks to see if the given vScale is valid for the given region."
    if (isinstance(args.vscale, list)):
        oldvscale = args.vscale[0]
    else:
        oldvscale = int(args.vscale)
    (lcds, elevds) = getDataset(args.region)
    lcds = None
    elevBand = elevds.GetRasterBand(1)
    elevCMinMax = elevBand.ComputeRasterMinMax(False)
    elevBand = None
    elevds = None
    elevMax = elevCMinMax[1]
    vscale = min(oldvscale, elevMax)
    vscale = max(vscale, (elevMax/maxelev)+1)
    if (vscale != oldvscale):
        print "Warning: vertical scale of %d for region %s is invalid -- changed to %d" % (oldvscale, args.region, vscale)
    args.vscale = vscale
    return vscale

# main
def main(argv):
    "The main portion of the script."

    default_scale = 6
    default_vscale = 6
    default_maxdepth = 10
    default_slope = 1
    default_tile = [256, 256]
    default_start = [0, 0]
    default_end = [0, 0]
    default_processes = cpu_count()

    parser = argparse.ArgumentParser(description='Generate images for BuildWorld.js from USGS datasets.')
    parser.add_argument('--region', nargs='?', type=checkDataset, help='a region to be processed (leave blank for list of regions)')
    parser.add_argument('--processes', nargs=1, default=default_processes, type=int, help="number of processes to spawn (default %d)" % default_processes)
    parser.add_argument('--scale', nargs=1, default=default_scale, type=int, help="horizontal scale factor (default %d)" % default_scale)
    parser.add_argument('--vscale', nargs=1, default=default_vscale, type=int, help="vertical scale factor (default %d)" % default_vscale)
    parser.add_argument('--maxdepth', nargs=1, default=default_maxdepth, type=int, help="maximum depth (default %d)" % default_maxdepth)
    parser.add_argument('--slope', nargs=1, default=default_slope, type=int, help="underwater slope factor (default %d)" % default_slope)
    parser.add_argument('--tile', nargs=2, default=default_tile, type=int, help="tile size in tuple form (default %s)" % (default_tile,))
    parser.add_argument('--start', nargs=2, default=default_start, type=int, help="start tile in tuple form (default %s)" % (default_start,))
    parser.add_argument('--end', nargs=2, default=default_end, type=int, help="end tile in tuple form (default %s)" % (default_end,))
    args = parser.parse_args()

    # list regions if requested
    if (args.region == None):
        listDatasets(dsDict)
        return 0

    # set up all the values
    rows, cols = getDatasetDims(args.region)
    processes = checkProcesses(args)
    (scale, mult) = checkScale(args)
    vscale = checkVScale(args)
    maxdepth = checkMaxDepth(args)
    slope = checkSlope(args)
    tileShape = checkTile(args, mult)
    (tileRows, tileCols) = tileShape
    (minTileRows, minTileCols, maxTileRows, maxTileCols) = checkStartEnd(args, mult, tileShape)

    # make imagedir
    imagedir = os.path.join("Images", args.region)
    # TODO: error checking here
    if os.path.exists(imagedir):
        [ os.remove(os.path.join(imagedir,name)) for name in os.listdir(imagedir) ]
    else:
        os.makedirs(imagedir)

    print "Processing region %s of size (%d, %d) with %d processes..." % (args.region, rows, cols, processes)

    # build crust tree for the whole map
    makeCrustIDT(args)

    if (processes == 1):
        [processTile(args, imagedir, tileRowIndex, tileColIndex) for tileRowIndex in xrange(minTileRows, maxTileRows) for tileColIndex in xrange(minTileCols, maxTileCols)]
    else:
        pool = Pool(processes)
        tasks = [(args, imagedir, tileRowIndex, tileColIndex) for tileRowIndex in xrange(minTileRows, maxTileRows) for tileColIndex in xrange(minTileCols, maxTileCols)]
        results = pool.imap_unordered(processTilestar, tasks)
        bleah = [x for x in results]
            
    print "Render complete -- total array of %d tiles was %d x %d" % ((maxTileRows-minTileRows)*(maxTileCols-minTileCols), int(rows*mult), int(cols*mult))

if __name__ == '__main__':
    UseExceptions()
    sys.exit(main(sys.argv))
