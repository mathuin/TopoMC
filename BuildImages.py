#!/usr/bin/env python
# mklcelevdata.py - 2010Jan21 - mathuin@gmail.com

# this script builds arrays for land cover and elevation

from __future__ import division
import os
import re
import sys
import numpy
import Image
import argparse
from osgeo import gdal
from osgeo import osr
from osgeo.gdalconst import *
from invdisttree import *
from multiprocessing import Pool, cpu_count
gdal.UseExceptions()

# paths for datasets
dsPaths = ['Datasets', '../TopoMC-Datasets']

# functions
def getDatasetDict(dspaths):
    "Given a list of paths, generate a dict of datasets."

    lcdirre = '\d\d\d\d\d\d\d\d'
    elevdirre = 'NED_\d\d\d\d\d\d\d\d'

    retval = {}
    for dspath in dspaths:
        regions = [ name for name in os.listdir(dspath) if os.path.isdir(os.path.join(dspath, name)) ]
        for region in regions:
            dsregion = os.path.join(dspath, region)
            lcfile = ''
            elevfile = ''
            elevorigfile = ''
            subdirs = [ name for name in os.listdir(os.path.join(dsregion)) if os.path.isdir(os.path.join(dsregion, name)) ]
            for subdir in subdirs:
                dsregionsub = os.path.join(dsregion, subdir)
                if re.match(lcdirre, subdir):
                    maybelcfile = os.path.join(dsregionsub, subdir+'.tif')
                    if (os.path.isfile(maybelcfile)):
                        lcfile = maybelcfile
                if re.match(elevdirre, subdir):
                    maybeelevfile = os.path.join(dsregionsub, subdir+'.tif')
                    if (os.path.isfile(maybeelevfile)):
                        elevfile = maybeelevfile
                        maybeelevorigfile = os.path.join(dsregionsub, subdir+'.tif-orig')
                        if (os.path.isfile(maybeelevorigfile)):
                            elevorigfile = maybeelevorigfile
            if (lcfile != '' and elevfile != '' and elevorigfile != ''):
                # check that both datasets open read-only without errors
                lcds = gdal.Open(lcfile)
                if (lcds == None):
                    print "%s: lc dataset didn't open" % region
                    break
                elevds = gdal.Open(elevfile)
                if (elevds == None):
                    print "%s: elev dataset didn't open" % region
                    break
                # check that both datasets have the same projection
                lcGeogCS = osr.SpatialReference(lcds.GetProjectionRef()).CloneGeogCS()
                elevGeogCS = osr.SpatialReference(elevds.GetProjectionRef()).CloneGeogCS()
                if (not lcGeogCS.IsSameGeogCS(elevGeogCS)):
                    print "%s: lc and elevation maps do not have the same projection" % region
                    break
                # calculate rows and columns
                rows = lcds.RasterXSize
                cols = lcds.RasterYSize
                # clean up
                lcds = None
                elevds = None
                retval[region] = [lcfile, elevfile, rows, cols]
    return retval

def getDataset(region):
    "Given a region name, return a tuple of datasets: (lc, elev)"
    if (region in dsDict):
        dsList = dsDict[region]
        return (gdal.Open(dsList[0], GA_ReadOnly), gdal.Open(dsList[1], GA_ReadOnly))
    else:
        return None

def getDatasetDims(region):
    "Given a region name, return dataset dimensions."
    if (region in dsDict):
        dsList = dsDict[region]
        return (dsList[2], dsList[3])
    else:
        return None

def getIDT(ds, offset, size, vScale=1):
    "Convert a portion of a given dataset (identified by corners) to an inverse distance tree."
    # retrieve data from dataset
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])
    Band = None

    # build initial arrays
    LatLong = getLatLongArray(ds, (offset), (size), 1)
    Value = Data.flatten()

    # scale elevation vertically
    Value = Value / vScale

    # build tree
    IDT = Invdisttree(LatLong, Value)

    return IDT

def getLatLongArray(ds, offset, size, mult=1):
    "Given transformations, dimensions, and multiplier, generate the interpolated array."
    rows = numpy.linspace(offset[1]/mult, (offset[1]+size[1])/mult, size[1], False)
    cols = numpy.linspace(offset[0]/mult, (offset[0]+size[0])/mult, size[0], False)
    retval = numpy.array([getLatLong(ds, row, col) for row in rows for col in cols])

    return retval

def getLatLong(ds, x, y):
    "Given dataset and coordinates, return latitude and longitude.  Based on GDALInfoReportCorner() from gdalinfo.py"
    (Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    dfGeoX = GeoTrans[0] + GeoTrans[1] * x + GeoTrans[2] * y
    dfGeoY = GeoTrans[3] + GeoTrans[4] * x + GeoTrans[5] * y
    pnt = Trans.TransformPoint(dfGeoX, dfGeoY, 0)
    return pnt[1], pnt[0]

def getTransforms(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Trans = osr.CoordinateTransformation(Proj, LatLong)
    ArcTrans = osr.CoordinateTransformation(LatLong, Proj)
    GeoTrans = ds.GetGeoTransform()

    return Trans, ArcTrans, GeoTrans

def getOffsetSize(ds, corners, mult=1):
    "Convert corners to offset and size."
    (ul, lr) = corners
    offset_x, offset_y = getCoords(ds, ul[0], ul[1])
    if (offset_x < 0):
        offset_x = 0
    if (offset_y < 0):
        offset_y = 0
    farcorner_x, farcorner_y = getCoords(ds, lr[0], lr[1])
    if (farcorner_x > ds.RasterXSize):
        farcorner_x = ds.RasterXSize
    if (farcorner_y > ds.RasterYSize):
        farcorner_y = ds.RasterYSize
    offset = (int(offset_x*mult), int(offset_y*mult))
    size = (farcorner_x*mult-offset_x*mult, farcorner_y*mult-offset_y*mult)
    if (size[0] < 0 or size[1] < 0):
        print "DEBUG: negative size is bad!"
    return offset, size

def getCoords(ds, lat, lon):
    (Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    "The backwards version of getLatLong, from geo_trans.c."
    pnt = ArcTrans.TransformPoint(lon, lat, 0)
    x = (pnt[0] - GeoTrans[0])/GeoTrans[1]
    y = (pnt[1] - GeoTrans[3])/GeoTrans[5]
    return int(x), int(y)

def getImageArray(ds, idtCorners, baseArray, nnear, vScale=1):
    "Given the relevant information, builds the image array."

    Offset, Size = getOffsetSize(ds, idtCorners)
    IDT = getIDT(ds, Offset, Size, vScale)
    ImageArray = IDT(baseArray, nnear=nnear, eps=.1)

    return ImageArray

def getTileOffsetSize(rowIndex, colIndex, tileShape, maxRows, maxCols, mult=1, idtPad=0):
    "run this with idtPad=0 to generate image."
    imageRows = tileShape[0]
    imageCols = tileShape[1]
    imageLeft = rowIndex*imageRows-idtPad
    imageRight = imageLeft+imageRows+2*idtPad
    imageUpper = colIndex*imageCols-idtPad
    imageLower = imageUpper+imageCols+2*idtPad
    if (imageLeft < 0):
        imageLeft = 0
    if (imageRight > maxRows):
        imageRight = maxRows
    if (imageUpper < 0):
        imageUpper = 0
    if (imageLower > maxCols):
        imageLower = maxCols
    imageOffset = (imageLeft, imageUpper)
    imageSize = (imageRight-imageLeft, imageLower-imageUpper)
    return imageOffset, imageSize

def listDatasets(dsdict):
    "Given a dataset dict, list the datasets and their dimensions."
    print 'Valid datasets detected:'
    dsDimsDict = dict((region, getDatasetDims(region)) for region in dsDict.keys())
    print "\n".join(["\t%s (%d, %d)" % (region, dsDimsDict[region][0], dsDimsDict[region][1]) for region in sorted(dsDict.keys())])

def checkDataset(string):
    "Checks to see if the supplied string is a dataset."
    if (string != None and not string in dsDict):
        listDatasets(dsDict)
        raise argparse.error("%s is not a valid dataset" % string)
    return string

def checkProcesses(args):
    "Checks to see if the given process count is valid."
    if (isinstance(args.processes, list)):
        processes = args.processes[0]
    else:
        processes = int(args.processes)
    return processes

def checkScale(args):
    "Checks to see if the given scale is valid for the given region.  Returns scale and multiplier."
    if (isinstance(args.scale, list)):
        scale = args.scale[0]
    else:
        scale = int(args.scale)
    lcds, elevds = getDataset(args.region)
    elevds = None
    lcTrans, lcArcTrans, lcGeoTrans = getTransforms(lcds)
    lcds = None
    lcperpixel = int(lcGeoTrans[1])
    if (scale > lcperpixel):
        print "Warning: scale of %d exceeds maximum for region %s -- changed to %d" % (scale, args.region, lcperpixel)
        scale = lcperpixel
    # FIXME: ensure that wierd values are okay
    # right now, restrict it to factors of lcperpixel
    if (lcperpixel/scale != lcperpixel//scale):
        for x in range(scale, lcperpixel+1):
            if (lcperpixel/x == lcperpixel//x):
                print "Warning: scale for region %s must be factor of %d -- changed to %d" % (args.region, lcperpixel, x)
                scale = x
                break
    mult = lcperpixel//scale
    return (scale, mult)

def checkVScale(args):
    "Checks to see if the given vScale is valid for the given region."
    if (isinstance(args.vscale, list)):
        vscale = args.vscale[0]
    else:
        vscale = int(args.vscale)
    (lcds, elevds) = getDataset(args.region)
    lcds = None
    elevBand = elevds.GetRasterBand(1)
    elevCMinMax = elevBand.ComputeRasterMinMax(False)
    elevBand = None
    elevds = None
    elevMax = elevCMinMax[1]
    if (elevMax/vscale > 60):
        newvscale = int(elevMax/60)-1 
        print "Warning: vscale value for region %s is %d too low -- changed to %d" % (args.region, vscale, newvscale)
        vscale = newvscale
    if (elevMax/vscale < 1):
        newvscale = elevMax
        print "Warning: vscale value for region %s is %d too low -- changed to %d" % (args.region, vscale, newvscale)
        vscale = newvscale
    return vscale

def checkTile(args, mult):
    "Checks to see if a tile dimension is too big for a region."
    tilex, tiley = args.tile
    rows, cols = getDatasetDims(args.region)
    maxRows = rows * mult
    maxCols = cols * mult
    tooLarge = False
    if (tilex > maxRows):
        tooLarge = True
        tilex = maxRows
    if (tiley > maxCols):
        tooLarge = True
        tiley = maxCols
    if (tooLarge):
        print "Warning: tile size for region %s is too large -- changed to %d, %d" % (args.region, tilex, tiley)
    return (tilex, tiley)

def checkStartEnd(args, mult, tile):
    "Checks to see if start and end values are valid for a region."
    (rows, cols) = getDatasetDims(args.region)
    (minTileRows, minTileCols) = args.start
    (maxTileRows, maxTileCols) = args.end
    (tileRows, tileCols) = tile

    numRowTiles = int((rows*mult+tileRows-1)/tileRows)
    numColTiles = int((cols*mult+tileCols-1)/tileCols)
    if (maxTileRows == 0 or maxTileRows > numRowTiles):
        if (maxTileRows > numRowTiles):
            print "Warning: maxTileRows greater than numTileRows, setting to %d" % numTileRows
        maxTileRows = numRowTiles
    if (minTileRows > maxTileRows):
        print "Warning: minTileRows less than maxTileRows, setting to %d" % maxTileRows
        minTileRows = maxTileRows
    if (maxTileCols == 0 or maxTileCols > numColTiles):
        if (maxTileCols > numColTiles):
            print "Warning: maxTileCols greater than numTileCols, setting to %d" % numTileCols
        maxTileCols = numColTiles
    if (minTileCols > maxTileCols):
        print "Warning: minTileCols less than maxTileCols, setting to %d" % maxTileCols
        minTileCols = maxTileCols
    return (minTileRows, minTileCols, maxTileRows, maxTileCols)

def processTile(args, tileShape, mult, vscale, imagedir, tileRowIndex, tileColIndex):
    "Actually process a tile."
    (lcds, elevds) = getDataset(args.region)
    (rows, cols) = getDatasetDims(args.region)
    maxRows = rows*mult
    maxCols = cols*mult
    baseOffset, baseSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols)
    idtOffset, idtSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols, idtPad=16)
    print "Generating tile (%d, %d) with dimensions (%d, %d)..." % (tileRowIndex, tileColIndex, baseSize[0], baseSize[1])

    baseShape = (baseSize[1], baseSize[0])
    baseArray = getLatLongArray(lcds, baseOffset, baseSize, mult)

    # these points are scaled coordinates
    idtUL = getLatLong(lcds, idtOffset[0]/mult, idtOffset[1]/mult)
    idtLR = getLatLong(lcds, (idtOffset[0]+idtSize[0])/mult, (idtOffset[1]+idtSize[1])/mult)

    # nnear=1 for landcover, 11 for elevation
    lcImageArray = getImageArray(lcds, (idtUL, idtLR), baseArray, 1)
    lcImageArray.resize(baseShape)

    # nnear=1 for landcover, 11 for elevation
    elevImageArray = getImageArray(elevds, (idtUL, idtLR), baseArray, 11, vscale)
    elevImageArray.resize(baseShape)

    # TODO: go through the arrays for some special transmogrification
    
    # save images
    lcImage = Image.fromarray(lcImageArray)
    lcImage.save(os.path.join(imagedir, 'lc-%d-%d.gif' % (baseOffset[0], baseOffset[1])))
    elevImage = Image.fromarray(elevImageArray)
    elevImage.save(os.path.join(imagedir, 'elev-%d-%d.gif' % (baseOffset[0], baseOffset[1])))

def processTilestar(args):
    return processTile(*args)

# main
def main(argv):
    "The main portion of the script."

    default_scale = 6
    default_vscale = 6
    default_tile = [256, 256]
    default_start = [0, 0]
    default_end = [0, 0]
    default_processes = cpu_count()

    parser = argparse.ArgumentParser(description='Generate images for BuildWorld.js from USGS datasets.')
    parser.add_argument('region', nargs='?', type=checkDataset, help='a region to be processed (leave blank for list of regions)')
    parser.add_argument('--processes', nargs=1, default=default_processes, type=int, help="number of processes to spawn (default %d)" % default_processes)
    parser.add_argument('--scale', nargs=1, default=default_scale, type=int, help="horizontal scale factor (default %d)" % default_scale)
    parser.add_argument('--vscale', nargs=1, default=default_vscale, type=int, help="vertical scale factor (default %d)" % default_vscale)
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
    tileShape = checkTile(args, mult)
    (tileRows, tileCols) = tileShape
    (minTileRows, minTileCols, maxTileRows, maxTileCols) = checkStartEnd(args, mult, tileShape)

    # make imagedir
    # TODO: add error checking
    imagedir = os.path.join("Images", args.region)
    if not os.path.exists(imagedir):
        os.makedirs(imagedir)

    pool = Pool(processes)
    print "Processing region %s of size (%d, %d) with %d processes..." % (args.region, rows, cols, processes)

    tasks = [(args, tileShape, mult, vscale, imagedir, tileRowIndex, tileColIndex) for tileRowIndex in range(minTileRows, maxTileRows) for tileColIndex in range(minTileCols, maxTileCols)]

    results = pool.imap_unordered(processTilestar, tasks)

    bleah = [x for x in results]
            
    print "Render complete -- total array of %d tiles was %d x %d" % ((maxTileRows-minTileRows)*(maxTileCols-minTileCols), rows*mult, cols*mult)

if __name__ == '__main__':
    dsDict = getDatasetDict(dsPaths)

    sys.exit(main(sys.argv))
