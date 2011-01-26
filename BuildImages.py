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
    (Trans, ArcTranss, GeoTrans) = getTransforms(ds)
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

def getLatLongArray(transform, geotransform, offset, size, mult):
    "Given transformations, dimensions, and multiplier, generate the interpolated array."

    rows = scaleRange(offset[1], size[1], mult)
    cols = scaleRange(offset[0], size[0], mult)
    retval = numpy.array([getLatLong(transform, geotransform, row, col) for row in rows for col in cols])
    return retval

def OLDscaleRange(offset, size, mult):
    "Used for building interpolation arrays."
    if ((mult % 2) == 1):
        edge = (mult//2)/mult
    else:
        edge = (mult-1)/(mult*2)

    # trimming edges
    print "DEBUG: offset is %f, size is %f, mult is %f, edge is %f" % (offset, size, mult, edge)
    #retval = list(numpy.linspace(offset-edge,offset+size-1+edge,num=mult*size))
    retval = list(numpy.linspace(offset,offset+size-1,num=((mult*size)-2)))
    print "DEBUG: retval length is %d" % len(retval)

    return retval

def scaleRange(offset, size, mult):
    "Used for building interpolation arrays."
    multSize = int(size*mult)
    retval = [offset+x/mult for x in range(multSize)]
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

def getOffsetSize(ds, corners):
    "Convert corners to offset and size."
    (ul, ur, ll, lr) = corners
    (Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    offset_x, offset_y = getCoords(ArcTrans, GeoTrans, ul[0], ul[1])
    if (offset_x < 0):
        print "DEBUG: offset_x was %d" % offset_x
        offset_x = 0
    if (offset_y < 0):
        print "DEBUG: offset_y was %d" % offset_y
        offset_y = 0
    farcorner_x, farcorner_y = getCoords(ArcTrans, GeoTrans, lr[0], lr[1])
    if (farcorner_x > ds.RasterXSize):
        print "DEBUG: farcorner_x was %d" % farcorner_x
        farcorner_x = ds.RasterXSize
    if (farcorner_y > ds.RasterYSize):
        print "DEBUG: farcorner_y was %d" % farcorner_y
        farcorner_y = ds.RasterYSize
    offset = (offset_x, offset_y)
    size = (farcorner_x-offset_x, farcorner_y-offset_y)
    return offset, size

def getCoords(transform, geotransform, lat, lon):
    "The backwards version of getLatLong, from geo_trans.c."
    pnt = transform.TransformPoint(lon, lat, 0)
    print "DEBUG: pnt[0] is %d, pnt[1] is %d" % (pnt[0], pnt[1])
    x = (pnt[0] - geotransform[0]+1)//geotransform[1]
    y = (pnt[1] - geotransform[3]-1)//geotransform[5]
    print "DEBUG: x is %d, y is %d" % (x, y)
    return int(x), int(y)

def getTiles(ds, mult, tileShape, idtPad=16):
    "Given a dataset, generates a list of tuples of the form: ((row, col), (imageUL, imageUR, imageLL, imageLR), (idtUL, idtUR, idtLL, idtLR))."
    imageRows=tileShape[0]
    imageCols=tileShape[1]
    Trans, ArcTrans, GeoTrans = getTransforms(ds)
    maxRows = ds.RasterXSize*mult
    maxCols = ds.RasterYSize*mult
    print "DEBUG: maxRows is %d, maxCols is %d" % (maxRows, maxCols)
    listTiles = []
    numRowTiles = int((maxRows+imageRows-1)/imageRows)
    numColTiles = int((maxCols+imageCols-1)/imageCols)
    print "DEBUG: numRowTiles is %d, numColTiles is %d" % (numRowTiles, numColTiles)
    rowIndex = 0
    colIndex = 0
    rows = scaleRange(0, numRowTiles, mult)
    cols = scaleRange(0, numColTiles, mult)
    for rowIndex in range(len(rows)):
        for colIndex in range(len(cols)):
            print "DEBUG: rowIndex is %d, colIndex is %d" % (rowIndex, colIndex)
            row = rows[rowIndex]
            col = cols[colIndex]
            print "DEBUG: row is %f, cols is %f" % (row, col)
            imageLeft = row*imageRows
            print "DEBUG: imageLeft was %f" % imageLeft
            if (imageLeft < 0):
                print "DEBUG: imageLeft was corrected!"
                imageLeft = 0
            print "DEBUG: imageLeft is %f" % imageLeft
            imageRight = (row+1)*imageRows
            print "DEBUG: imageRight was %f" % imageRight
            if (imageRight > maxRows):
                imageRight = maxRows
            print "DEBUG: imageRight is %f" % imageRight
            imageUpper = col*imageCols
            print "DEBUG: imageUpper was %f" % imageUpper
            if (imageUpper < 0):
                print "DEBUG: imageUpper was corrected!"
                imageUpper = 0
            print "DEBUG: imageUpper is %f" % imageUpper
            imageLower = (col+1)*imageCols
            print "DEBUG: imageLower was %f" % imageLower
            if (imageLower > maxCols):
                imageLower = maxCols
            print "DEBUG: imageLower is %f" % imageLower
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
            # convert edges to lat/long corners
            imageUL = getLatLong(Trans, GeoTrans, imageLeft, imageUpper)
            imageLL = getLatLong(Trans, GeoTrans, imageLeft, imageLower)
            imageUR = getLatLong(Trans, GeoTrans, imageRight, imageUpper)
            imageLR = getLatLong(Trans, GeoTrans, imageRight, imageLower)
            idtUL = getLatLong(Trans, GeoTrans, idtLeft, idtUpper)
            idtLL = getLatLong(Trans, GeoTrans, idtLeft, idtLower)
            idtUR = getLatLong(Trans, GeoTrans, idtRight, idtUpper)
            idtLR = getLatLong(Trans, GeoTrans, idtRight, idtLower)
            listTiles.append(((rowIndex, colIndex),
                              (imageUL, imageLL, imageUR, imageLR),
                              (idtUL, idtLL, idtUR, idtLR)))
    print "DEBUG: listTiles has length %d" % (len(listTiles))
    #print "DEBUG: indices of listTiles:", ['(%d, %d)' % (rowIndex, colIndex) for ((rowIndex, colIndex), (imageLeft, imageRight, imageUpper, imageLower), (idtLeft, idtRight, idtUpper, idtLower)) in listTiles]
    print "DEBUG: image corners of listTiles[0]:", ['((%f, %f), (%f, %f), (%f, %f), (%f, %f))' % (imageUL[0], imageUL[1], imageLL[0], imageLL[1], imageUR[0], imageUR[1], imageLR[0], imageLR[1]) for ((rowIndex, colIndex), (imageUL, imageLL, imageUR, imageLR), (idtUL, idtLL, idtUR, idtLR)) in listTiles]
    return listTiles

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

    # tinker time!
    tileShape = (256, 256)
    myTiles = getTiles(lcds, mult, tileShape)

    for tile in myTiles:
        ((row, col), imageCorners, idtCorners) = tile
        tileRow = row * tileShape[0]
        tileCol = col * tileShape[1]

        # build base array (based on landcover)
        baseOffset, baseSize = getOffsetSize(lcds, imageCorners)
        baseShape = (baseSize[1], baseSize[0])
        print "DEBUG: baseOffset is %d, %d" % (baseOffset)
        print "DEBUG: baseSize is %d, %d" % (baseSize)
        baseArray = getLatLongArray(lcTrans, lcGeoTrans, baseOffset, baseSize, mult)

        # nnear=1 for landcover, 11 for elevation
        lcOffset, lcSize = getOffsetSize(lcds, idtCorners)
        print "DEBUG: lcOffset is %d, %d" % (lcOffset)
        print "DEBUG: lcSize is %d, %d" % (lcSize)
        lcIDT = getIDT(lcds, lcOffset, lcSize)
        lcImageArray = lcIDT(baseArray, nnear=1, eps=.1).reshape(baseShape)
        lcImage = Image.fromarray(lcImageArray)
        lcImage.save('Images/%s-lc-%d-%d.gif' % (region, tileRow, tileCol))

        elevOffset, elevSize = getOffsetSize(elevds, idtCorners)
        print "DEBUG: elevOffset is %d, %d" % (elevOffset)
        print "DEBUG: elevSize is %d, %d" % (elevSize)
        elevIDT = getIDT(elevds, elevOffset, elevSize, vScale)
        elevImageArray = elevIDT(baseArray, nnear=11, eps=.1).reshape(baseShape)
        elevImage = Image.fromarray(elevImageArray)
        elevImage.save('Images/%s-elev-%d-%d.gif' % (region, tileRow, tileCol))

if __name__ == '__main__':
    sys.exit(main(sys.argv))
