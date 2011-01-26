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

# constants
#FIXME: (consider retrieving this from transform?)
lcperpixel = 30 # meters per pixel in landcover file 
scale = 6 # with 30m data, use 6 or 10 or maybe 30

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
def getIDT(ds, offset, size, baseArray, hScale, vScale=0):
    "Convert a portion of a given dataset (identified by offset and size) to an inverse distance tree."
    # TODO: move maximum elevation test *outside* getImage/getArrays

    # retrieve data from dataset
    (Transform, GeoTransform, Data) = getTransformsAndData(ds, offset, size)

    # helper variables
    # mental note, we want Y,X here!
    sizeRow = size[1]
    sizeCol = size[0]

    # build initial arrays
    LatLong = getLatLongArray(Transform, GeoTransform, (offset), (size), 1)
    # TODO: might just be able to use Data.flatten()!
    #Value = numpy.array(([Data[row][col] for row in range(sizeRow) for col in range(sizeCol)]))
    Value = Data.flatten()

    # scale elevation vertically
    if (vScale != 0):
        Value = Value / vScale

    # build tree
    IDT = Invdisttree(LatLong, Value)

    return IDT

def getLatLongArray(transform, geotransform, offset, size, mult):
    "Given transformations, dimensions, and multiplier, generate the interpolated array."
    # Never forget it's Y,X
    startRow = offset[1]
    sizeRow = size[1]
    startCol = offset[0]
    sizeCol = size[0]

    rows = scaleRange(startRow, sizeRow, mult)
    cols = scaleRange(startCol, sizeCol, mult)
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

def getArrays(lcds, elevds, hScale, vScale=0):
    "Given roughly coincident datasets for land cover and elevation, this function returns two arrays (land cover and elevation respectively) registered to the land cover locations and scaled if desired."
    # sigh!
    if (vScale == 0):
        vScale = hScale
    # calculate hMult and check it
    # FIXME: do after reading in land cover?
    hMult = lcperpixel//hScale
    if (hMult % 2 != 1):
        print "Error: scaling factor must be odd!"
        sys.exit()
    # calculate hStep
    hStep = hMult//2

    # get elevation data
    (elevT, elevGeoT, elevData) = getTransformsAndData(elevds)
    elevLatLongList = []
    elevValue = []

    for rowIndex in range(elevData.shape[0]):
        for colIndex in range(elevData.shape[1]):
            (newLat, newLong) = getLatLong(elevT, elevGeoT, rowIndex, colIndex)
            elevLatLongList.append([newLat, newLong])
            elevValue.append(elevData[rowIndex][colIndex])

    # check for altitude problems
    if ((elevData.max()/vScale) > 64):
        newvScale = elevData.max()//64
        print "Warning: vertical scale of %d insufficient, using %d instead" % (vScale, newvScale)
        vScale = newvScale

    # build elevation arrays
    elevLatLong = numpy.array(elevLatLongList)
    elevValue = numpy.array(elevValue) / vScale

    # build elevation IDT
    elevIDT = Invdisttree(elevLatLong, elevValue)
    
    # get land cover data
    (lcT, lcGeoT, lcData) = getTransformsAndData(lcds)
    # TODO: check to see if lc and elev have same shape!
    # FIXME: newshape will depend on new rectangle
    lcLatLongList = []
    lcValueList = []
    lcSortMeList = []

    # build land cover array
    for rowIndex in range(lcData.shape[0]):
        for colIndex in range(lcData.shape[1]):
            for multRow in range(-1*hStep,hStep+1):
                for multCol in range(-1*hStep,hStep+1):
                    newRow = rowIndex + (multRow/hMult)
                    newCol = colIndex + (multCol/hMult)
                    (newLat, newLong) = getLatLong(lcT, lcGeoT, newRow, newCol)
                    lcLatLongList.append([newLat, newLong])
                    lcValueList.append(lcData[rowIndex][colIndex])
                    lcSortMeList.append([newRow, newCol])

    # build land cover array
    lcSortMe = numpy.array(lcSortMeList)
    lcLatLongInds = numpy.lexsort((lcSortMe[:,1], lcSortMe[:,0]))
    lcLatLong = numpy.array(lcLatLongList)[lcLatLongInds]
    lcArr = numpy.array(lcValueList)[lcLatLongInds].reshape(hMult*lcData.shape[0], hMult*lcData.shape[1])

    # compute elevation array from inverse distance tree
    elevArr = elevIDT(lcLatLong, nnear=8, eps=.1).reshape(hMult*lcData.shape[0], hMult*lcData.shape[1])

    # return the two arrays
    return lcArr, elevArr

def getTransformsAndData(ds, offset=(0,0), size=(0,0)):
    "Given a dataset, return the transform and geotransform."
    if (size == (0,0)):
        size = (ds.RasterXSize, ds.RasterYSize)
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Transform = osr.CoordinateTransformation(Proj, LatLong)
    GeoTransform = ds.GetGeoTransform()
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])
    Band = None

    return Transform, GeoTransform, Data

def getTransforms(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Transform = osr.CoordinateTransformation(Proj, LatLong)
    GeoTransform = ds.GetGeoTransform()

    return Transform, GeoTransform

def getLatLong(transform, geotransform, x, y):
    "Given transform, geotransform, and coordinates, return latitude and longitude.  Based on GDALInfoReportCorner() from gdalinfo.py"
    dfGeoX = geotransform[0] + geotransform[1] * x + geotransform[2] * y
    dfGeoY = geotransform[3] + geotransform[4] * x + geotransform[5] * y
    pnt = transform.TransformPoint(dfGeoX, dfGeoY, 0)
    return pnt[1], pnt[0]

# here we go!
if (len(sys.argv) != 2):
    region = 'BlockIsland'
else:
    region = sys.argv[1]
lcds = locateDataset(region)
if (lcds == None):
    print "Error: no land cover dataset found matching %s!" % region
    sys.exit()
elevds = locateDataset(region, 'NED_')
if (elevds == None):
    print "Error: no elevation dataset found matching %s!" % region
    sys.exit()
# FIXME: should check to see if they have the same projection?!
# FIXME: should do elevation correction out here, sigh

# getArrays with one argument uses the same scale for horiz and vert
#lcdata, elevdata = getArrays(lcds, elevds, scale)
# use 30, 6 for testing
lcdata, elevdata = getArrays(lcds, elevds, 30, 6)

# forced horizontal scale of 30 and vertical scale of 6 for testing
# FIXME: should apply scale factor here!
hScale = 30
vScale = 6
mult = lcperpixel//hScale

# build base array
lcTransform, lcGeoTransform = getTransforms(lcds)
baseShape = (mult*lcds.RasterYSize, mult*lcds.RasterXSize)
baseArray = getLatLongArray(lcTransform, lcGeoTransform, (0, 0), (lcds.RasterXSize, lcds.RasterYSize), mult)
lcIDT = getIDT(lcds, (0, 0), (lcds.RasterXSize, lcds.RasterYSize), baseArray, hScale)
# nnear=1 for landcover
lcImageArray = lcIDT(baseArray, nnear=1, eps=.1).reshape(baseShape)
lcImage = Image.fromarray(lcImageArray)
lcImage.save('Images/'+region+'-new-test-lcimage.gif')
elevIDT = getIDT(elevds, (0, 0), (elevds.RasterXSize, elevds.RasterYSize), baseArray, hScale, vScale)
elevImageArray = elevIDT(baseArray, nnear=11, eps=.1).reshape(baseShape)
elevImage = Image.fromarray(elevImageArray)
elevImage.save('Images/'+region+'-new-test-elevimage.gif')

# now that we have the data, let's turn it into happy image stuff
lcimage = Image.fromarray(lcdata)
lcimage.save('Images/'+region+'-test-lcimage.gif')
elevimage = Image.fromarray(elevdata)
elevimage.save('Images/'+region+'-test-elevimage.gif')
