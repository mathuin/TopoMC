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
    for path, dirs, files in os.walk(os.path.abspath(('Datasets/'+region))):
        for filename in fnmatch.filter(files, prefix+"[0-9]*.tif"):
            dsfilename = os.path.join(path, filename)
    return gdal.Open(dsfilename, GA_ReadOnly)

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

def getTransformsAndData(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Transform = osr.CoordinateTransformation(Proj, LatLong)
    GeoTransform = ds.GetGeoTransform()
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    Band = None

    return Transform, GeoTransform, Data

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
elevds = locateDataset(region, 'NED_')
# getArrays with one argument uses the same scale for horiz and vert
#lcdata, elevdata = getArrays(lcds, elevds, scale)
# use 30, 6 for testing
lcdata, elevdata = getArrays(lcds, elevds, 30, 6)

# now that we have the data, let's turn it into happy image stuff
lcimage = Image.fromarray(lcdata)
lcimage.save('Images/'+region+'-test-lcimage.gif')
elevimage = Image.fromarray(elevdata)
elevimage.save('Images/'+region+'-test-elevimage.gif')
