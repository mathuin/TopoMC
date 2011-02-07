# dataset module

import os
import re
from osgeo import gdal, osr
from osgeo.gdalconst import *
from coords import getTransforms

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
