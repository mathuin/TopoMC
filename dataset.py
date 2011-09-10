# dataset module

import os
import re
from argparse import ArgumentError
from osgeo import gdal, osr
from osgeo.gdalconst import *
from coords import getTransforms
from tempfile import NamedTemporaryFile
import logging
logging.basicConfig(level=logging.WARNING)
datasetlogger = logging.getLogger('dataset')

# paths for datasets
dsPaths = ['Datasets', '../TopoMC-Datasets']

# product types in order of preference
# NB: only seamless types are being considered at present
#     next version should handle tiled!
# landcover IDs are:
# L04 - 2001 version 2.0 (should work just fine)
# L01 - 2001 (currently the only one fully supported)
# L92 - 1992 http://www.mrlc.gov/nlcd92_leg.php (01 and 06 for other two!)
# L6L - 2006
# need to abstract out terrain.py!
landcoverIDs = ['L07', 'L04', 'L01', 'L92', 'L6L']
# JMT - 2011Aug29 - ND9 is not working, commenting out
#elevationIDs = ['ND3', 'NED', 'NAK', 'ND9']
elevationIDs = ['ND9', 'ND3', 'NED', 'NAK']

# functions
def decodeLayerID(layerID):
    "Given a layer ID, return the product type, image type, metadata type, and compression type."
    productID = layerID[0]+layerID[1]+layerID[2]
    if (productID in landcoverIDs):
        pType = "landcover"
    elif (productID in elevationIDs):
        pType = "elevation"
    else:
        datasetlogger.error("Invalid product ID %s" % productID)
        return -1

    imagetype = layerID[3]+layerID[4]
    # only 02-GeoTIFF (tif) known to work
    if (imagetype == "02"):
        iType = "tif"
    elif (imagetype == "01"):
        iType = "arc"
    elif (imagetype == "03"):
        iType = "bil"
    elif (imagetype == "05"):
        iType = "GridFloat"
    elif (imagetype == "12"):
        iType = "IMG"
    elif (imagetype == "15"):
        iType = "bil_16int"
    else:
        datasetlogger.error("Invalid image type %s" % imagetype)
        return -1
        
    metatype = layerID[5]
    if (metatype == "A"):
        mType = "ALL"
    elif (metatype == "F"):
        mType = "FAQ"
    elif (metatype == "H"):
        mType = "HTML"
    elif (metatype == "S"):
        mType = "SGML"
    elif (metatype == "T"):
        mType = "TXT"
    elif (metatype == "X"):
        mType = "XML"
    else:
        datasetlogger.error("Invalid metadata type %s" % metatype)
        return -1

    compressiontype = layerID[6]
    if (compressiontype == "T"):
        cType = "TGZ"
    elif (compressiontype == "Z"):
        cType = "ZIP"
    else:
        datasetlogger.error("Invalid compression type %s" % compressiontype)
        return -1

    return (pType, iType, mType, cType)

def getDatasetDir(region):
    "Given a list of paths, and a region, retrieve the dataset dir.  Return -1 if no regiondir found."
    for dspath in dsPaths:
        if not os.path.exists(dspath):
            continue
        regions = [ name for name in os.listdir(dspath) if os.path.isdir(os.path.join(dspath, name)) ]
        if region in regions:
            return os.path.join(dspath, region)
    return -1

def getDatasetDict():
    "Given a list of paths, generate a dict of datasets."

    retval = {}
    for dspath in dsPaths:
        if not os.path.exists(dspath):
            continue
        regions = [ name for name in os.listdir(dspath) if os.path.isdir(os.path.join(dspath, name)) ]
        for region in regions:
            dsregion = os.path.join(dspath, region)
            layerIDs = [ name for name in os.listdir(dsregion) if os.path.isdir(os.path.join(dsregion, name)) ]
            elevfile = ""
            lcfile = ""
            for layerID in layerIDs:
                (pType, iType, mType, cType) = decodeLayerID(layerID)
                dataname = os.path.join(dsregion, layerID, "%s.%s" % (layerID, iType))
                if (pType == "elevation"):
                    elevfile = dataname
                elif (pType == "landcover"):
                    lcfile = dataname
                else:
                    datasetlogger.error("%s: unsupported product type %s found" % (region, pType))
                    return -1
            if (elevfile == ""):
                datasetlogger.error("%s: elevation image not found" % region)
                return -1
            if (lcfile == ""):
                datasetlogger.error("%s: landcover image not found" % region)
                return -1
            # check that both datasets open read-only without errors
            lcds = gdal.Open(lcfile, GA_ReadOnly)
            if (lcds == None):
                datasetlogger.error("%s: lc dataset didn't open" % region)
                break
            elevds = gdal.Open(elevfile, GA_ReadOnly)
            if (elevds == None):
                datasetlogger.error( "%s: elev dataset didn't open" % region)
                break
            # check that both datasets have the same projection
            lcGeogCS = osr.SpatialReference(lcds.GetProjectionRef()).CloneGeogCS()
            elevGeogCS = osr.SpatialReference(elevds.GetProjectionRef()).CloneGeogCS()
            if (not lcGeogCS.IsSameGeogCS(elevGeogCS)):
                datasetlogger.error("%s: lc and elevation maps do not have the same projection" % region)
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
    # NB: do not change to logger
    print 'Valid datasets detected:'
    dsDimsDict = dict((region, getDatasetDims(region)) for region in dsDict.keys())
    print "\n".join(["\t%s (%d, %d)" % (region, dsDimsDict[region][0], dsDimsDict[region][1]) for region in sorted(dsDict.keys())])

def checkDataset(string):
    "Checks to see if the supplied string is a dataset."
    if (string != None and not string in dsDict):
        listDatasets(dsDict)
        raise ArgumentError("%s is not a valid dataset" % string)
    return string

def warpFileNew(source, dest, like):
    "Warp the source file to the destination file to match the third file.  WARNING: does not appear to work!"
    # stolen from warp.py in GDAL
    hDataset = gdal.Open(like, GA_ReadOnly)
    pszProjection = hDataset.GetProjectionRef()
    hSRS = osr.SpatialReference()
    if hSRS.ImportFromWkt(pszProjection) == gdal.CE_None:
        dst_wkt = hSRS.ExportToPrettyWkt(False)
    else:
        dst_wkt = pszProjection
    hDataset = None
    hSRS = None

    src_ds = gdal.Open(source, GA_ReadOnly)

    error_threshold = 0.125
    resampling = gdal.GRA_Cubic

    tmp_ds = gdal.AutoCreateWarpedVRT(src_ds, None, dst_wkt, resampling, error_threshold)
    dst_xsize = tmp_ds.RasterXSize
    dst_ysize = tmp_ds.RasterYSize
    dst_gt = tmp_ds.GetGeoTransform()
    tmp_ds = None

    # destination file uses same driver as source file
    driver = src_ds.GetDriver()

    dst_ds = driver.Create(dest, dst_xsize, dst_ysize, src_ds.RasterCount)
    dst_ds.SetProjection(dst_wkt)
    dst_ds.SetGeoTransform(dst_gt)

    gdal.ReprojectImage(src_ds, dst_ds, None, None, resampling, 0, error_threshold)
    src_ds = None
    dst_ds = None

def warpFile(source, dest, like):
    "Warp the source file to match the like file and write to the dest file."
    prffd = NamedTemporaryFile(delete=False)
    prfname = prffd.name
    prffd.close()
    os.system('gdalinfo %s | sed -e "1,/Coordinate System is:/d" -e "/Origin =/,\$d" | xargs echo > %s' % (like, prfname))
    os.system('gdalwarp -srcnodata -340282346638528859811704183484516925440.000 -dstnodata 0 -t_srs %s -r cubic %s %s' % (prfname, source, dest))
    os.remove(prfname)

    
# initialize
dsDict = getDatasetDict()
