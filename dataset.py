# dataset module

import os
import re
from osgeo import gdal, osr
from osgeo.gdalconst import *
from coords import getTransforms

# paths for datasets
dsPaths = ['Datasets', '../TopoMC-Datasets']

# product types in order of preference
landcoverIDs = ['L01']
elevationIDs = ['ND3', 'NED']

# functions
def decodeLayerID(layerID):
    "Given a layer ID, return the product type, image type, metadata type, and compression type."
    productID = layerID[0]+layerID[1]+layerID[2]
    if (productID in landcoverIDs):
        pType = "landcover"
    elif (productID in elevationIDs):
        pType = "elevation"
    else:
        print "Invalid product ID %s" % productID
        return -1

    # FIXME: handle more image types
    imagetype = layerID[3]+layerID[4]
    if (imagetype == "02"):
        iType = "tif"
    else:
        print "Invalid image type %s" % imagetype
        return -1
        
    metatype = layerID[5]
    if (metatype == "H"):
        mType = "HTML"
    elif (metatype == "T"):
        mType = "TXT"
    elif (metatype == "X"):
        mType = "XML"
    else:
        print "Invalid metadata type %s" % metatype
        return -1

    compressiontype = layerID[6]
    if (compressiontype == "Z"):
        cType = "ZIP"
    elif (compressiontype == "T"):
        cType = "TGZ"
    else:
        print "Invalid compression type %s" % compressiontype
        return -1

    return (pType, iType, mType, cType)

def getDatasetDict(dspaths):
    "Given a list of paths, generate a dict of datasets."

    retval = {}
    for dspath in dspaths:
        if not os.path.exists(dspath):
            continue
        regions = [ name for name in os.listdir(dspath) if os.path.isdir(os.path.join(dspath, name)) ]
        for region in regions:
            dsregion = os.path.join(dspath, region)
            lcfile = ''
            elevfile = ''
            elevorigfile = ''
            layerids = [ name for name in os.listdir(dsregion) if os.path.isdir(os.path.join(dsregion, name)) ]
            for layerid in layerids:
                dsregionlayerid = os.path.join(dsregion, layerid)
                (pType, iType, mType, cType) = decodeLayerID(layerid)
                subdirs = [ name for name in os.listdir(dsregionlayerid) if os.path.isdir(os.path.join(dsregionlayerid, name)) ]
                for subdir in subdirs:
                    dsregionsub = os.path.join(dsregionlayerid, subdir)
                    if (pType == "landcover"):
                        maybelcfile = os.path.join(dsregionsub, "%s.%s" % (subdir, iType))
                        if (os.path.isfile(maybelcfile)):
                            lcfile = maybelcfile
                    if (pType == "elevation"):
                        maybeelevfile = os.path.join(dsregionsub, "%s.%s" % (subdir, iType))
                        if (os.path.isfile(maybeelevfile)):
                            elevfile = maybeelevfile
                        maybeelevorigfile = os.path.join(dsregionsub, "%s.%s-orig" % (subdir, iType))

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
                # nodata - just lc here
                nodata = int(lcds.GetRasterBand(lcds.RasterCount).GetNoDataValue())
                # clean up
                lcds = None
                elevds = None
                retval[region] = [lcfile, elevfile, rows, cols, nodata]
    return retval

def getDataset(region):
    "Given a region name, return a tuple of datasets: (lc, elev)"
    if (region in dsDict):
        dsList = dsDict[region]
        dsOne = gdal.Open(dsList[0], GA_ReadOnly)
        dsOne.transforms = getTransforms(dsOne)
        dsTwo = gdal.Open(dsList[1], GA_ReadOnly)
        dsTwo.transforms = getTransforms(dsTwo)
        return (dsOne, dsTwo)
    else:
        return None

def getDatasetDims(region):
    "Given a region name, return dataset dimensions."
    if (region in dsDict):
        dsList = dsDict[region]
        return (dsList[2], dsList[3])
    else:
        return None

def getDatasetNodata(region):
    "Given a region name, return the nodata value."
    if (region in dsDict):
        dsList = dsDict[region]
        return dsList[4]
    else:
        return None

def listDatasets(dsdict):
    "Given a dataset dict, list the datasets and their dimensions."
    print 'Valid datasets detected:'
    dsDimsDict = dict((region, getDatasetDims(region)) for region in dsDict.keys())
    print "\n".join(["\t%s (%d, %d)" % (region, dsDimsDict[region][0], dsDimsDict[region][1]) for region in sorted(dsDict.keys())])

def checkDataset(string):
    "Checks to see if the supplied string is a dataset."
    if (string != None and not string in dsDict):
        listDatasets(dsDict)
        argparse.error("%s is not a valid dataset" % string)
    return string

# initialize
dsDict = getDatasetDict(dsPaths)
