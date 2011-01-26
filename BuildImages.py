#!/usr/bin/env python
# mklcelevdata.py - 2010Jan21 - mathuin@gmail.com

# this script builds arrays for land cover and elevation

from __future__ import division
import os
import fnmatch
import sys
import struct
import numpy
import Image
from osgeo import gdal
from osgeo import osr
from osgeo.gdalconst import *
from invdisttree import *
gdal.UseExceptions()

# functions
def locateDataset(region, prefix=""):
    "Given a region name and an optional prefix, returns the dataset for that region."
    # NB: assumed that exactly one dataset exists for each region/prefix
    dsfilename = ''
    dspaths = ['Datasets', '../TopoMC-Datasets']
    for dspath in dspaths:
        for path, dirs, files in os.walk(os.path.abspath((dspath+'/'+region))):
            for filename in fnmatch.filter(files, prefix+"[0-9]*.tif"):
                dsfilename = os.path.join(path, filename)
    # no dataset found
    if (dsfilename == ''):
        return None
    return gdal.Open(dsfilename, GA_ReadOnly)

# this now has to return the IDT, not the array, sigh
def getIDT(ds, offset, size, vScale=1):
    "Convert a portion of a given dataset (identified by corners) to an inverse distance tree."
    # retrieve data from dataset
    (Transform, ArcTransforms, GeoTransform) = getTransforms(ds)
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])
    Band = None

    # build initial arrays
    LatLong = getLatLongArray(Transform, GeoTransform, (offset), (size), 1)
    Value = Data.flatten()

    # scale elevation vertically
    Value = Value / vScale

    # build tree
    IDT = Invdisttree(LatLong, Value)

    return IDT

def getLatLongArray(transform, geotransform, offset, size, mult):
    "Given transformations, dimensions, and multiplier, generate the interpolated array."

    rows = scaleRange(offset[1], size[1], mult)
    cols = scaleRange(offset[0], size[0], mult)
    retval = numpy.array([getLatLong(transform, geotransform, row, col) for row in rows for col in cols])
    return retval

def scaleRange(offset, size, mult):
    "Used for building interpolation arrays."
    if ((mult % 2) == 1):
        edge = (mult//2)/mult
    else:
        edge = (mult-1)/(mult*2)

    retval = list(numpy.linspace(offset-edge,offset+size-1+edge,num=mult*size))

    return retval

def getTransforms(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Transform = osr.CoordinateTransformation(Proj, LatLong)
    ArcTransform = osr.CoordinateTransformation(LatLong, Proj)
    GeoTransform = ds.GetGeoTransform()

    return Transform, ArcTransform, GeoTransform

def getLatLong(transform, geotransform, x, y):
    "Given transform, geotransform, and coordinates, return latitude and longitude.  Based on GDALInfoReportCorner() from gdalinfo.py"
    dfGeoX = geotransform[0] + geotransform[1] * x + geotransform[2] * y
    dfGeoY = geotransform[3] + geotransform[4] * x + geotransform[5] * y
    pnt = transform.TransformPoint(dfGeoX, dfGeoY, 0)
    return pnt[1], pnt[0]

def getOffsetSize(ds, corners):
    "Convert corners to offset and size."
    (ul, ur, ll, lr) = corners
    (Transform, ArcTransform, GeoTransform) = getTransforms(ds)
    offset = getCoords(ArcTransform, GeoTransform, ul[0], ul[1])
    farcorner = getCoords(ArcTransform, GeoTransform, lr[0], lr[1])
    size = (farcorner[0]-offset[0], farcorner[1]-offset[1])
    return offset, size

def getCoords(transform, geotransform, lat, lon):
    "The backwards version of getLatLong, from geo_trans.c."
    pnt = transform.TransformPoint(lon, lat, 0)
    x = (pnt[0] - geotransform[0]+1)//geotransform[1]
    y = (pnt[1] - geotransform[3]-1)//geotransform[5]
    print "DEBUG: x is %d, y is %d" % (x, y)
    return int(x), int(y)

def getTiles(ds, mult, tileShape, idtPad=16):
    "Given a dataset, generates a list of tuples of the form: ((row, col), (imageUL, imageUR, imageLL, imageLR), (idtUL, idtUR, idtLL, idtLR))."
    imageRows=tileShape[0]
    imageCols=tileShape[1]
    Transform, ArcTransform, GeoTransform = getTransforms(ds)
    maxRows = ds.RasterXSize*mult
    maxCols = ds.RasterYSize*mult
    print "DEBUG: maxRows is %d, maxCols is %d" % (maxRows, maxCols)
    listTiles = []
    numRowTiles = int((maxRows+imageRows-1)/imageRows)
    numColTiles = int((maxCols+imageCols-1)/imageCols)
    print "DEBUG: numRowTiles is %d, numColTiles is %d" % (numRowTiles, numColTiles)
    for row in scaleRange(0, numRowTiles, mult):
        for col in scaleRange(0, numColTiles, mult):
            imageLeft = row*imageRows
            imageRight = (row+1)*imageRows
            if (imageRight > maxRows):
                imageRight = maxRows
            imageUpper = col*imageCols
            imageLower = (col+1)*imageCols
            if (imageLower > maxCols):
                imageLower = maxCols
            idtLeft = row*imageRows-idtPad
            if (idtLeft < 0):
                idtLeft = 0
            idtRight = (row+1)*imageRows+idtPad
            if (idtRight > maxRows):
                idtRight = maxRows
            idtUpper = col*imageCols-idtPad
            if (idtUpper < 0):
                idtUpper = 0
            idtLower = (col+1)*imageCols+idtPad
            if (idtLower > maxCols):
                idtLower = maxCols
            imageUL = getLatLong(Transform, GeoTransform, imageLeft, imageUpper)
            imageUR = getLatLong(Transform, GeoTransform, imageRight, imageUpper)
            imageLL = getLatLong(Transform, GeoTransform, imageLeft, imageLower)
            imageLR = getLatLong(Transform, GeoTransform, imageRight, imageLower)
            idtUL = getLatLong(Transform, GeoTransform, idtLeft, idtUpper)
            idtUR = getLatLong(Transform, GeoTransform, idtRight, idtUpper)
            idtLL = getLatLong(Transform, GeoTransform, idtLeft, idtLower)
            idtLR = getLatLong(Transform, GeoTransform, idtRight, idtLower)
            listTiles.append(((row, col),
                              (imageLeft, imageRight, imageUpper, imageLower),
                              (imageUL, imageUR, imageLL, imageLR),
                              (idtLeft, idtRight, idtUpper, idtLower),
                              (idtUL, idtUR, idtLL, idtLR)))
    return listTiles

# here we go!
if (len(sys.argv) != 2):
    region = 'BlockIsland'
else:
    region = sys.argv[1]

# locate datasets
lcds = locateDataset(region)
if (lcds == None):
    print "Error: no land cover dataset found matching %s!" % region
    sys.exit()
elevds = locateDataset(region, 'NED_')
if (elevds == None):
    print "Error: no elevation dataset found matching %s!" % region
    sys.exit()

# do both datasets have the same projection?
lcGeogCS = osr.SpatialReference(lcds.GetProjectionRef()).CloneGeogCS()
elevGeogCS = osr.SpatialReference(elevds.GetProjectionRef()).CloneGeogCS()

if (not lcGeogCS.IsSameGeogCS(elevGeogCS)):
    print "Error: land cover and elevation maps do not have the same projection."
    sys.exit()

# set up scaling factors
# horizontal based on land cover
# vertical based on elevation
# FIXME: need to traverse entire elevation map to get max
# --- how to do this efficiently
lcTransform, lcArcTransform, lcGeoTransform = getTransforms(lcds)
lcperpixel = lcGeoTransform[1]
# forced horizontal scale of 30 and vertical scale of 6 for testing
hScale = 30
vScale = 6
mult = lcperpixel//hScale

tileShape = (256, 256)
myTiles = getTiles(lcds, mult, tileShape)

for tile in myTiles:
    ((row, col), imageEdges, imageCorners, idtEdges, idtCorners) = tile
    print "DEBUG: imageEdges are %d, %d, %d, %d" % (imageEdges)
    print "DEBUG: idtEdges are %d, %d, %d, %d" % (idtEdges)

    # build base array (based on landcover)
    baseOffset, baseSize = getOffsetSize(lcds, imageCorners)
    baseShape = (baseSize[1], baseSize[0])
    # FIXME: still using tileShape instead of tileShape
    print "DEBUG: baseOffset is %d, %d" % (baseOffset)
    print "DEBUG: baseSize is %d, %d" % (baseSize)
    baseArray = getLatLongArray(lcTransform, lcGeoTransform, baseOffset, tileShape, mult)

    # nnear=1 for landcover, 11 for elevation
    lcOffset, lcSize = getOffsetSize(lcds, idtCorners)
    print "DEBUG: lcOffset is %d, %d" % (lcOffset)
    print "DEBUG: lcSize is %d, %d" % (lcSize)
    lcIDT = getIDT(lcds, lcOffset, lcSize)
    lcImageArray = lcIDT(baseArray, nnear=1, eps=.1).reshape(tileShape)
    lcImage = Image.fromarray(lcImageArray)
    lcImage.save('Images/%s-lc-%d-%d.gif' % (region, row, col))

    elevOffset, elevSize = getOffsetSize(elevds, idtCorners)
    print "DEBUG: elevOffset is %d, %d" % (elevOffset)
    print "DEBUG: elevSize is %d, %d" % (elevSize)
    elevIDT = getIDT(elevds, elevOffset, elevSize, vScale)
    elevImageArray = elevIDT(baseArray, nnear=11, eps=.1).reshape(tileShape)
    elevImage = Image.fromarray(elevImageArray)
    elevImage.save('Images/%s-elev-%d-%d.gif' % (region, row, col))

