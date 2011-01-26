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

def getIDT(ds, offset, size, vScale=1):
    "Convert a portion of a given dataset (identified by corners) to an inverse distance tree."
    # retrieve data from dataset
    (Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])
    Band = None

    # build initial arrays
    LatLong = getLatLongArray(Trans, GeoTrans, (offset), (size), 1)
    Value = Data.flatten()

    # scale elevation vertically
    Value = Value / vScale

    # build tree
    IDT = Invdisttree(LatLong, Value)

    return IDT

def getLatLongArray(transform, geotransform, offset, size, mult=1):
    "Given transformations, dimensions, and multiplier, generate the interpolated array."
    rows = list(numpy.linspace(offset[1]/mult, (offset[1]+size[1])/mult, size[1], False))
    cols = list(numpy.linspace(offset[0]/mult, (offset[0]+size[0])/mult, size[0], False))
    retval = numpy.array([getLatLong(transform, geotransform, row, col) for row in rows for col in cols])

    return retval

def getTransforms(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Trans = osr.CoordinateTransformation(Proj, LatLong)
    ArcTrans = osr.CoordinateTransformation(LatLong, Proj)
    GeoTrans = ds.GetGeoTransform()

    return Trans, ArcTrans, GeoTrans

def getLatLong(transform, geotransform, x, y):
    "Given transform, geotransform, and coordinates, return latitude and longitude.  Based on GDALInfoReportCorner() from gdalinfo.py"
    dfGeoX = geotransform[0] + geotransform[1] * x + geotransform[2] * y
    dfGeoY = geotransform[3] + geotransform[4] * x + geotransform[5] * y
    pnt = transform.TransformPoint(dfGeoX, dfGeoY, 0)
    return pnt[1], pnt[0]

def getOffsetSize(ds, corners, mult=1):
    "Convert corners to offset and size."
    (ul, lr) = corners
    (Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    print "DEBUG: upper left corner is %f, %f" % (ul[0], ul[1])
    print "DEBUG: lower right corner is %f, %f" % (lr[0], lr[1])
    offset_x, offset_y = getCoords(ArcTrans, GeoTrans, ul[0], ul[1])
    print "DEBUG: offset_x, offset_y are %d, %d" % (offset_x, offset_y)
    if (offset_x < 0):
        print "DEBUG: offset_x was %d" % offset_x
        offset_x = 0
    if (offset_y < 0):
        print "DEBUG: offset_y was %d" % offset_y
        offset_y = 0
    farcorner_x, farcorner_y = getCoords(ArcTrans, GeoTrans, lr[0], lr[1])
    print "DEBUG: farcorner_x, farcorner_y are %d, %d" % (farcorner_x, farcorner_y)
    if (farcorner_x > ds.RasterXSize):
        print "DEBUG: farcorner_x was %d" % farcorner_x
        farcorner_x = ds.RasterXSize
    if (farcorner_y > ds.RasterYSize):
        print "DEBUG: farcorner_y was %d" % farcorner_y
        farcorner_y = ds.RasterYSize
    # FIXME: something smells here
    offset = (int(offset_x*mult), int(offset_y*mult))
    size = (farcorner_x*mult-offset_x*mult, farcorner_y*mult-offset_y*mult)
    if (size[0] < 0 or size[1] < 0):
        print "DEBUG: negative size is bad!"
    return offset, size

def getCoords(transform, geotransform, lat, lon):
    "The backwards version of getLatLong, from geo_trans.c."
    pnt = transform.TransformPoint(lon, lat, 0)
    #print "DEBUG: pnt[0] is %d, pnt[1] is %d" % (pnt[0], pnt[1])
    x = (pnt[0] - geotransform[0])/geotransform[1]
    y = (pnt[1] - geotransform[3])/geotransform[5]
    #print "DEBUG: x is %d, y is %d" % (x, y)
    return int(x), int(y)

def OLDgetTiles(ds, mult, tileShape, idtPad=16):
    "Given a dataset, generates a list of tuples of the form: ((row, col), (imageUL, imageLL, imageUR, imageLR), (idtUL, idtLL, idtUR, idtLR))."
    imageRows=tileShape[0]
    imageCols=tileShape[1]
    (Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    maxRows = ds.RasterXSize*mult
    maxCols = ds.RasterYSize*mult
    print "DEBUG: maxRows is %d, maxCols is %d" % (maxRows, maxCols)
    listTiles = []
    numRowTiles = int((maxRows+imageRows-1)/imageRows)
    numColTiles = int((maxCols+imageCols-1)/imageCols)
    print "DEBUG: numRowTiles is %d, numColTiles is %d" % (numRowTiles, numColTiles)
    for rowIndex in range(numRowTiles):
        for colIndex in range(numColTiles):
            imageLeft = rowIndex*imageRows
            imageRight = imageLeft+imageRows
            imageUpper = colIndex*imageCols
            imageLower = imageUpper+imageCols
            imageLeftOld = imageLeft
            imageRightOld = imageRight
            imageUpperOld = imageUpper
            imageLowerOld = imageLower
            if (imageLeft < 0):
                print "DEBUG: imageLeft was corrected!"
                imageLeft = 0
            if (imageRight > maxRows):
                imageRight = maxRows
            if (imageUpper < 0):
                print "DEBUG: imageUpper was corrected!"
                imageUpper = 0
            if (imageLower > maxCols):
                imageLower = maxCols
            idtLeft = imageLeft-idtPad
            if (idtLeft < 0):
                idtLeft = 0
            idtRight = imageRight+idtPad
            if (idtRight > maxRows):
                idtRight = maxRows
            idtUpper = imageUpper-idtPad
            if (idtUpper < 0):
                idtUpper = 0
            idtLower = imageLower+idtPad
            if (idtLower > maxCols):
                idtLower = maxCols
            imageOffset = (imageLeft, imageUpper)
            imageSize = ((imageRight-imageLeft), (imageLower-imageUpper))
            # quick check
            badTile = False
            if (imageSize[0] < 0 or imageSize[1] < 0):
                print "DEBUG: image (%d, %d) has negative size?!?" % (rowIndex, colIndex)
                badTile = True
            if (imageSize != tileShape and rowIndex != (numRowTiles-1) and colIndex != (numColTiles-1)):
                print "DEBUG: image (%d, %d) has non-standard shape for no good reason!" % (rowIndex, colIndex)
                badTile = True
            if (badTile):
                print "DEBUG: image for (%d, %d) was (%f, %f, %f, %f)" % (rowIndex, colIndex, imageLeftOld, imageRightOld, imageUpperOld, imageLowerOld)
                print "DEBUG: image is (%f, %f, %f, %f)" % (imageLeft, imageRight, imageUpper, imageLower)
                print "DEBUG: edges = (%f, %f, %f, %f)" % (imageLeft, imageRight, imageUpper, imageLower)
                print "DEBUG: offset = (%f, %f), size = (%f, %f)" % (imageLeft, imageUpper, imageRight-imageLeft, imageLower-imageUpper)
            # convert edges to lat/long corners
            realUL = getLatLong(Trans, GeoTrans, 0, 0)
            realLR = getLatLong(Trans, GeoTrans, ds.RasterXSize, ds.RasterYSize)
            imageUL = getLatLong(Trans, GeoTrans, imageLeft/mult, imageUpper/mult)
            imageLR = getLatLong(Trans, GeoTrans, imageRight/mult, imageLower/mult)
            idtUL = getLatLong(Trans, GeoTrans, idtLeft/mult, idtUpper/mult)
            idtLR = getLatLong(Trans, GeoTrans, idtRight/mult, idtLower/mult)
            listTiles.append(((rowIndex, colIndex),
                              (imageUL, imageLR),
                              (idtUL, idtLR)))
    return listTiles

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

# main
def main(argv):
    "The main portion of the script."

    # default region is supplied with TopoMC
    if (len(argv) != 2):
        region = 'BlockIsland'
    else:
        region = argv[1]

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
    lcTrans, lcArcTrans, lcGeoTrans = getTransforms(lcds)
    lcperpixel = lcGeoTrans[1]
    # forced horizontal scale of 30 and vertical scale of 6 for testing
    hScale = 10
    vScale = 6
    mult = lcperpixel//hScale

    tileShape = (256, 256)
    # NEW IDEA
    imageRows=tileShape[0]
    imageCols=tileShape[1]
    maxRows = lcds.RasterXSize*mult
    maxCols = lcds.RasterYSize*mult
    print "DEBUG: maxRows is %d, maxCols is %d" % (maxRows, maxCols)
    numRowTiles = int((maxRows+imageRows-1)/imageRows)
    numColTiles = int((maxCols+imageCols-1)/imageCols)
    print "DEBUG: numRowTiles is %d, numColTiles is %d" % (numRowTiles, numColTiles)
    for rowIndex in range(numRowTiles):
        for colIndex in range(numColTiles):
            print "DEBUG: rowIndex is %d, colIndex is %d" % (rowIndex, colIndex)
            baseOffset, baseSize = getTileOffsetSize(rowIndex, colIndex, tileShape, maxRows, maxCols)
            idtOffset, idtSize = getTileOffsetSize(rowIndex, colIndex, tileShape, maxRows, maxCols, idtPad=16)

            baseShape = (baseSize[1], baseSize[0])
            print "DEBUG: baseShape is", baseShape
            baseArray = getLatLongArray(lcTrans, lcGeoTrans, baseOffset, baseSize, mult)
            print "DEBUG: baseArray shape is", baseArray.shape

            # these points are in super-big-coordinates
            idtUL = getLatLong(lcTrans, lcGeoTrans, idtOffset[0]/mult, idtOffset[1]/mult)
            idtLR = getLatLong(lcTrans, lcGeoTrans, (idtOffset[0]+idtSize[0])/mult, (idtOffset[1]+idtSize[1])/mult)

            # nnear=1 for landcover, 11 for elevation
            lcImageArray = getImageArray(lcds, (idtUL, idtLR), baseArray, 1)
            lcImageArray.resize(baseShape)
            lcImage = Image.fromarray(lcImageArray)
            lcImage.save('Images/%s-lc-%d-%d-%d-%d.gif' % (region, baseOffset[0], baseOffset[1], baseSize[0], baseSize[1]))

            # nnear=1 for landcover, 11 for elevation
            elevImageArray = getImageArray(elevds, (idtUL, idtLR), baseArray, 11, vScale)
            elevImageArray.resize(baseShape)
            elevImage = Image.fromarray(elevImageArray)
            elevImage.save('Images/%s-elev-%d-%d-%d-%d.gif' % (region, baseOffset[0], baseOffset[1], baseSize[0], baseSize[1]))

if __name__ == '__main__':
    sys.exit(main(sys.argv))
