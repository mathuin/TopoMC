#!/usr/bin/env python

from __future__ import division
from math import ceil, floor
import suds
import re
import os
import urllib,urllib2
import urlparse
import yaml
import logging
logging.basicConfig(level=logging.INFO)
from time import sleep
import zipfile
import tarfile
from utils import cleanmkdir, locate
from terrain import Terrain
from pymclevel import mclevel

from osgeo import gdal, osr
from osgeo.gdalconst import GDT_Int16, GA_ReadOnly
from bathy import getBathy
from crust import Crust
import numpy
#
from clidt import CLIDT

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def __init__(self):
        pass

    """stupid redirect handling craziness"""
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        result.headers = headers
        return result

class Region:
    """I have no idea what I'm doing here."""

    # coordinate systems
    wgs84 = 4326
    albers = 102039
    t_srs = "+proj=aea +datum=NAD83 +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +x_0=0 +y_0=0 +units=m"

    # raster layer order
    rasters = {'landcover': 1, 'elevation': 2, 'bathy': 3, 'crust': 4}
    
    # sadness
    zipfileBroken = False

    # default values
    tilesize = 256
    scale = 6
    vscale = 6
    trim = 0
    sealevel = 64
    maxdepth = 32

    # tileheight is height of map in Minecraft units
    tileheight = mclevel.MCInfdevOldLevel.Height
    # headroom is room between top of terrain and top of map
    headroom = 16

    # product types in order of preference
    productIDs = { 'elevation': ['N3F', 'N2F', 'N1F'],
                   'landcover': sorted(Terrain.translate.keys()) }
    # file suffix for extraction
    # FIXME: check N2F value
    exsuf = { 'N3F': '13', 'N2F': '12', 'N1F': '1' }

    # download directory
    downloaddir = os.path.join('Downloads')

    def __init__(self, name, xmax, xmin, ymax, ymin, tilesize=None, scale=None, vscale=None, trim=None, sealevel=None, maxdepth=None, lcIDs=None, elIDs=None, doOre=True, doSchematics=False):
        """Create a region based on lat-longs and other parameters."""
        # NB: smart people check names
        self.name = name

        # tile must be an even multiple of chunk width
        # chunkWidth not defined in pymclevel but is hardcoded everywhere
        if tilesize == None:
            tilesize = Region.tilesize
        else:
            if (tilesize % 16 != 0):
                raise AttributeError, 'bad tilesize %s' % tilesize
        self.tilesize = tilesize

        # scale can be any positive integer
        if scale == None:
            scale = Region.scale
        else:
            if (scale > 0):
                self.scale = int(scale)
            else:
                raise AttributeError, 'bad scale %s' % scale

        # sealevel and maxdepth are not checked until after files are retrieved
        if sealevel == None:
            sealevel = Region.sealevel
        else:
            self.sealevel = sealevel

        if maxdepth == None:
            maxdepth = Region.maxdepth
        else:
            self.maxdepth = maxdepth

        # trim and vscale are not checked until after files are retrieved
        if trim == None:
            trim = Region.trim
        else:
            self.trim = trim

        if vscale == None:
            vscale = Region.vscale
        else:
            self.vscale = vscale

        # disable overly dense elevation products
        self.productIDs = Region.productIDs
        # if (scale > 5):
        #     self.productIDs['elevation'].remove('ND9')
        if (scale > 15):
            self.productIDs['elevation'].remove('N3F')

        # specified IDs must be in region list
        if lcIDs == None:
            landcoverIDs = self.productIDs['landcover']
        else:
            landcoverIDs = [ ID for ID in lcIDs if ID in self.productIDs['landcover'] ]
            if landcoverIDs == []:
                raise AttributeError, 'invalid landcover ID'

        if elIDs == None:
            elevationIDs = self.productIDs['elevation']
        else:
            elevationIDs = [ ID for ID in elIDs if ID in self.productIDs['elevation'] ]
            if elevationIDs == []:
                raise AttributeError, 'invalid elevation ID'

        # enable or disable ore and schematics
        self.doOre = doOre
        self.doSchematics = doSchematics

        # crazy directory fun
        self.regiondir = os.path.join('Regions', self.name)
        cleanmkdir(self.regiondir)

        self.mapsdir = os.path.join(self.regiondir, 'Datasets')
        cleanmkdir(self.mapsdir)

        self.mapname = os.path.join(self.regiondir, 'Map.tif')

        # these are the latlong values
        self.llextents = { 'xmax': max(xmax, xmin), 'xmin': min(xmax, xmin), 'ymax': max(ymax, ymin), 'ymin': min(ymax, ymin) }

        # access the web service
        # NB: raise hell if it is inaccessible
        wsdlConv = "http://extract.cr.usgs.gov/XMLWebServices/Coordinate_Conversion_Service.asmx?WSDL"
        clientConv = suds.client.Client(wsdlConv)
        # This web service returns suds.sax.text.Text not XML sigh
        Convre = "<X Coordinate>(.*?)</X Coordinate > <Y Coordinate>(.*?)</Y Coordinate >"

        # convert from WGS84 to Albers
        ULdict = {'X_Value': self.llextents['xmin'], 'Y_Value': self.llextents['ymin'], 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        URdict = {'X_Value': self.llextents['xmax'], 'Y_Value': self.llextents['ymin'], 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        LLdict = {'X_Value': self.llextents['xmin'], 'Y_Value': self.llextents['ymax'], 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        LRdict = {'X_Value': self.llextents['xmax'], 'Y_Value': self.llextents['ymax'], 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (LRx, LRy) = re.findall(Convre, clientConv.service.getCoordinates(**LRdict))[0]

        # select maximum values for landcover extents
        xfloat = [float(x) for x in [ULx, URx, LLx, LRx]]
        yfloat = [float(y) for y in [ULy, URy, LLy, LRy]]
        mxmax = max(xfloat)
        mxmin = min(xfloat)
        mymax = max(yfloat)
        mymin = min(yfloat)

        # calculate tile edges
        realsize = self.scale * self.tilesize
        self.tiles = { 'xmax': int(ceil(mxmax / realsize)), 'xmin': int(floor(mxmin / realsize)), 'ymax': int(ceil(mymax / realsize)), 'ymin': int(floor(mymin / realsize)) }

        self.albersextents = { 'landcover': dict(), 'elevation': dict() }
        self.wgs84extents = { 'landcover': dict(), 'elevation': dict() }

        # landcover has a maxdepth-sized border
        self.albersextents['elevation'] = { 'xmax': self.tiles['xmax'] * realsize, 'xmin': self.tiles['xmin'] * realsize, 'ymax': self.tiles['ymax'] * realsize, 'ymin': self.tiles['ymin'] * realsize }
        borderwidth = self.maxdepth * self.scale
        self.albersextents['landcover'] = { 'xmax': self.albersextents['elevation']['xmax'] + borderwidth, 'xmin': self.albersextents['elevation']['xmin'] - borderwidth, 'ymax': self.albersextents['elevation']['ymax'] + borderwidth, 'ymin': self.albersextents['elevation']['ymin'] - borderwidth }

        # now convert back from Albers to WGS84
        for maptype in ['landcover', 'elevation']:
            ULdict = {'X_Value': self.albersextents[maptype]['xmin'], 'Y_Value': self.albersextents[maptype]['ymin'], 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
            (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
            URdict = {'X_Value': self.albersextents[maptype]['xmax'], 'Y_Value': self.albersextents[maptype]['ymin'], 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
            (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
            LLdict = {'X_Value': self.albersextents[maptype]['xmin'], 'Y_Value': self.albersextents[maptype]['ymax'], 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
            (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
            LRdict = {'X_Value': self.albersextents[maptype]['xmax'], 'Y_Value': self.albersextents[maptype]['ymax'], 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
            (LRx, LRy) = re.findall(Convre, clientConv.service.getCoordinates(**LRdict))[0]

            # select maximum values
            xfloat = [float(x) for x in [ULx, URx, LLx, LRx]]
            yfloat = [float(y) for y in [ULy, URy, LLy, LRy]]
            self.wgs84extents[maptype] = { 'xmax': max(xfloat), 'xmin': min(xfloat), 'ymax': max(yfloat), 'ymin': min(yfloat) }

        # check availability of product IDs and identify specific layer IDs
        self.lclayer = self.checkavail(landcoverIDs, 'landcover')
        self.ellayer = self.checkavail(elevationIDs, 'elevation')

        # write the values to the file
        stream = file(os.path.join(self.regiondir, 'Region.yaml'), 'w')
        yaml.dump(self, stream)
        stream.close()

    def decodeLayerID(self, layerID):
        """Given a layer ID, return the product type, image type, metadata type, and compression type."""
        productID = layerID[0]+layerID[1]+layerID[2]
        try:
            pType = [ product for product in self.productIDs.keys() if productID in self.productIDs[product] ][0]
        except IndexError:
            raise AttributeError, 'Invalid productID %s' % productID

        imagetype = layerID[3]+layerID[4]
        try:
            iType = [ image for image in Region.imageTypes.keys() if imagetype in Region.imageTypes[image] ][0]
        except IndexError:
            raise AttributeError, 'Invalid imagetype %s' % imagetype
        
        metatype = layerID[5]
        try:
            mType = [ meta for meta in Region.metaTypes.keys() if metatype in Region.metaTypes[meta] ][0]
        except IndexError:
            raise AttributeError, 'Invalid metatype %s' % metatype

        compressiontype = layerID[6]
        try:
            mType = [ compression for compression in Region.compressionTypes.keys() if compressiontype in Region.compressionTypes[compression] ][0]
        except IndexError:
            raise AttributeError, 'Invalid compressiontype %s' % compressiontype

        compressiontype = layerID[6]
        if (compressiontype == "T"):
            cType = "tgz"
        elif (compressiontype == "Z"):
            cType = "zip"
        else:
            raise AttributeError, 'Invalid compressiontype %s' % compressiontype
        
        return (pType, iType, mType, cType)

    def checkavail(self, productlist, maptype):
        """Check availability with web service."""
        mapextents = self.wgs84extents[maptype]

        # access the web service to check availability
        wsdlInv = "http://ags.cr.usgs.gov/index_service/Index_Service_SOAP.asmx?WSDL"
        clientInv = suds.client.Client(wsdlInv)

        # ensure desired attributes are present
        desiredAttributes = ['PRODUCTKEY','STATUS']
        attributes = []
        attributeList = clientInv.service.return_Attribute_List()
        for attribute in desiredAttributes:
            if attribute in attributeList[0]:
                attributes.append(attribute)
        if len(attributes) != len(desiredAttributes):
            raise AttributeError, "Not all attributes found"
    
        # return_attributes arguments dictionary
        rAdict = {'Attribs': ','.join(attributes), 'XMin': mapextents['xmin'], 'XMax': mapextents['xmax'], 'YMin': mapextents['ymin'], 'YMax': mapextents['ymax'], 'EPSG': Region.wgs84}
        rAatts = clientInv.service.return_Attributes(**rAdict)
        # store offered products in a list
        offered = []
        # this returns an array of custom attributes
        # which is apparently a ball full of crazy
        # NB: clean up this [0][0] crap!
        for elem in rAatts.ArrayOfCustomAttributes:
            if (elem[0][0][0] == 'PRODUCTKEY' and elem[0][0][1] in productlist and
                elem[0][1][0] == 'STATUS' and elem[0][1][1] == 'Tiled'):
                offered.append(elem[0][0][1])
        # this should extract the first
        try:
            productID = [ ID for ID in productlist if ID in offered ][0]
        except IndexError:
            raise AttributeError, "No products are available for this location!"
        return productID

    def requestvalidation(self, layerIDs):
        """Generates download URLs from layer IDs."""
        retval = {}

        # request validation
        wsdlRequest = "http://extract.cr.usgs.gov/requestValidationService/wsdl/RequestValidationService.wsdl"
        clientRequest = suds.client.Client(wsdlRequest)

        # we now iterate through layerIDs
        for layerID in layerIDs:
            layername = [key for key in self.productIDs.keys() if layerID in self.productIDs[key]][0]
            mapextents = self.wgs84extents[layername]
            xmlString = "<REQUEST_SERVICE_INPUT><AOI_GEOMETRY><EXTENT><TOP>%f</TOP><BOTTOM>%f</BOTTOM><LEFT>%f</LEFT><RIGHT>%f</RIGHT></EXTENT><SPATIALREFERENCE_WKID/></AOI_GEOMETRY><LAYER_INFORMATION><LAYER_IDS>%s</LAYER_IDS></LAYER_INFORMATION><CHUNK_SIZE>%d</CHUNK_SIZE><JSON></JSON></REQUEST_SERVICE_INPUT>" % (mapextents['ymax'], mapextents['ymin'], mapextents['xmin'], mapextents['xmax'], layerID, 250) # can be 100, 15, 25, 50, 75, 250

            response = clientRequest.service.getTiledDataDirectURLs2(xmlString)

            print "Requested URLs for layer ID %s..." % layerID

            # I am still a bad man.
            downloadURLs = [x.rsplit("</DOWNLOAD_URL>")[0] for x in response.split("<DOWNLOAD_URL>")[1:]]

            retval[layerID] = downloadURLs

        return retval

    @staticmethod
    def getfn(downloadURL):
        pdURL = urlparse.urlparse(downloadURL)
        pQS = urlparse.parse_qs(pdURL[4])
        longfile = pQS['FNAME'][0]
        justfile = os.path.split(longfile)[1]
        return justfile

    def retrievefile(self, layerID, downloadURL):
        """Retrieve the datafile associated with the URL.  This may require downloading it from the USGS servers or extracting it from a local archive."""
        fname = Region.getfn(downloadURL)
        layerdir = os.path.join(Region.downloaddir, layerID)
        # FIXME: do this more elegantly
        os.system('mkdir -p %s' % layerdir)
        downloadfile = os.path.join(layerdir, fname)
        if os.path.exists(downloadfile):
            print "Using cached file for layerID %s" % layerID
        else:
            print "Downloading file from server for layerID %s" % layerID
            try:
                (tempfile, message) = urllib.urlretrieve(downloadURL, downloadfile)
            except IOError, e:
                print "whoops!"
                raise IOError, e
            else:
                print "Download complete!"
        # FIXME: this is grotesque
        extracthead = fname.split('.')[0]
        # lame but works
        if layerID in Region.exsuf.keys():
            # elevation
            extractfiles = [os.path.join(extracthead, '.'.join(['float%s_%s' % (extracthead, Region.exsuf[layerID]), suffix])) for suffix in 'flt', 'hdr', 'prj']
        else:
            # landcover
            extractfiles = ['.'.join([extracthead, suffix]) for suffix in 'tif', 'tfw']
        for extractfile in extractfiles:
            if os.path.exists(os.path.join(layerdir, extractfile)):
                print "Using existing file %s for layerID %s" % (extractfile, layerID)
            else:
                os.system('unzip %s %s -d %s' % (downloadfile, extractfile, layerdir))
        return os.path.join(layerdir, extractfiles[0])

    def buildvrts(self):
        """Extracts image files and merges as necessary."""

        layerIDs = [ name for name in os.listdir(self.mapsdir) if os.path.isdir(os.path.join(self.mapsdir, name)) ]
        if layerIDs == []:
            raise IOError, 'No files found'
        for layerID in layerIDs:
            (pType, iType, mType, cType) = self.decodeLayerID(layerID)
            filesuffix = cType.lower()
            layerdir = os.path.join(self.mapsdir, layerID)
            compfiles = [ name for name in os.listdir(layerdir) if (os.path.isfile(os.path.join(layerdir, name)) and name.endswith(filesuffix)) ]
            for compfile in compfiles:
                (compbase, compext) = os.path.splitext(compfile)
                fullfile = os.path.join(layerdir, compfile)
                datasubdir = os.path.join(layerdir, compbase)
                compfile = '%s.%s' % (compbase, iType)
                # tar (at least) expects Unix pathnames
                compimage = '/'.join([compbase, compfile])
                cleanmkdir(datasubdir)
                if (Region.zipfileBroken == False):
                    if (cType == "tgz"):
                        cFile = tarfile.open(fullfile)
                    elif (cType == "zip"):
                        cFile = zipfile.ZipFile(fullfile)
                    cFile.extract(compimage, layerdir)
                    cFile.close()
                else:
                    if (cType == "tgz"):
                        cFile = tarfile.open(fullfile)
                        cFile.extract(compimage, layerdir)
                    elif (cType == "zip"):
                        omfgcompimage = os.path.join(compbase, compfile)
                        os.mkdir(os.path.dirname(os.path.join(datasubdir, compimage)))
                        cFile = zipfile.ZipFile(fullfile)
                        cFile.extract(omfgcompimage, datasubdir)
                        os.rename(os.path.join(datasubdir, omfgcompimage), os.path.join(layerdir, compimage))
                    cFile.close()
                # convert tif to good SRS
                rawfile = os.path.join(layerdir, compbase, compfile)
                goodfile = os.path.join(layerdir, compbase, "%s.good%s" % (compbase, iType))
                warpcmd = 'gdalwarp -q -multi -t_srs "%s" %s %s' % (Region.t_srs, rawfile, goodfile)
                os.system('%s' % warpcmd)

            vrtfile = os.path.join(layerdir, '%s.vrt' % layerID)
            buildvrtcmd = 'gdalbuildvrt %s %s' % (vrtfile, ' '.join(['"%s"' % x for x in locate('*.good*', root=layerdir)]))
            os.system('%s' % buildvrtcmd)

    def getfiles(self):
        """Get files from USGS and extract them if necessary."""
        layerIDs = [self.lclayer, self.ellayer]
        downloadURLs = self.requestvalidation(layerIDs)
        for layerID in downloadURLs.keys():
            extractlist = []
            for downloadURL in downloadURLs[layerID]:
                extractfile = self.retrievefile(layerID, downloadURL)
                extractlist.append(extractfile)
            # build VRTs here for now
            # will put back if good SRS nonsense still required
            print 'before vrt for ', layerID
            vrtfile = os.path.join(self.mapsdir, '%s.vrt' % layerID)
            buildvrtcmd = 'gdalbuildvrt %s %s' % (vrtfile, ' '.join([extractfile for extractfile in extractlist]))
            print 'build ', buildvrtcmd
            os.system('%s' % buildvrtcmd)
            print 'success?'
        # self.buildvrts()

    def buildmap(self, wantCL=True):
        """Use downloaded files and other parameters to build multi-raster map."""

        # warp elevation data into new format
        # NB: can't do this to landcover until mode algorithm is supported
        elvrt = os.path.join(self.mapsdir, '%s.vrt' % (self.ellayer)) 
        elfile = os.path.join(self.mapsdir, '%s.tif' % (self.ellayer))
        elextents = self.albersextents['elevation']
        warpcmd = 'gdalwarp -q -multi -t_srs "%s" -tr %d %d -te %d %d %d %d -r cubic %s %s -srcnodata "-340282346638529993179660072199368212480.000" -dstnodata 0' % (Region.t_srs, self.scale, self.scale, elextents['xmin'], elextents['ymin'], elextents['xmax'], elextents['ymax'], elvrt, elfile)

        try:
            os.remove(elfile)
        except OSError:
            pass
        # NB: make this work on Windows too!
        os.system("%s" % warpcmd)

        elds = gdal.Open(elfile, GA_ReadOnly)
        elgeotrans = elds.GetGeoTransform()
        elband = elds.GetRasterBand(1)
        elarray = elband.ReadAsArray(0, 0, elds.RasterXSize, elds.RasterYSize)
        (elysize, elxsize) = elarray.shape

        # update sealevel, trim and vscale
        elmin = elband.GetMinimum()
        elmax = elband.GetMaximum()
        if elmin is None or elmax is None:
            (elmin, elmax) = elband.ComputeRasterMinMax(False)
        elmin = int(elmin)
        elmax = int(elmax)
        elband = None
        elds = None

        # sealevel depends upon elmin
        minsealevel = 2
        # if minimum elevation is below sea level, add extra space
        if (elmin < 0):
            minsealevel += int(-1.0*elmin/self.scale)
        maxsealevel = Region.tileheight - Region.headroom
        oldsealevel = self.sealevel
        if (oldsealevel > maxsealevel or oldsealevel < minsealevel):
            print "warning: sealevel value %d outside %d-%d range" % (oldsealevel, minsealevel, maxsealevel)
        self.sealevel = int(min(max(oldsealevel, minsealevel), maxsealevel))

        # maxdepth depends upon sealevel
        minmaxdepth = 1
        maxmaxdepth = self.sealevel - 1
        oldmaxdepth = self.maxdepth
        if (oldmaxdepth > maxmaxdepth or oldmaxdepth < minmaxdepth):
            print "warning: maxdepth value %d outside %d-%d range" % (oldmaxdepth, minmaxdepth, maxmaxdepth)
        self.maxdepth = int(min(max(oldmaxdepth, minmaxdepth), maxmaxdepth))

        # trim depends upon elmin (if elmin < 0, trim == 0)
        mintrim = Region.trim
        maxtrim = max(elmin, mintrim)
        oldtrim = self.trim
        if (oldtrim > maxtrim or oldtrim < mintrim):
            print "warning: trim value %d outside %d-%d range" % (oldtrim, mintrim, maxtrim)
        self.trim = int(min(max(oldtrim, mintrim), maxtrim))

        # vscale depends on sealevel, trim and elmax
        # NB: no maximum vscale, the sky's the limit (hah!)
        eltrimmed = elmax - self.trim
        elroom = Region.tileheight - Region.headroom - self.sealevel
        minvscale = ceil(eltrimmed / elroom)
        oldvscale = self.vscale
        if (oldvscale < minvscale):
            print "warning: vscale value %d smaller than minimum value %d" % (oldvscale, minvscale)
        self.vscale = int(max(oldvscale, minvscale))

        # GeoTIFF
        # four bands: landcover, elevation, bathy, crust
        # data type is GDT_Int16 (elevation can be negative)
        driver = gdal.GetDriverByName("GTiff")
        mapds = driver.Create(self.mapname, elxsize, elysize, len(Region.rasters), GDT_Int16)
        # overall map transform should match elevation map transform
        mapds.SetGeoTransform(elgeotrans)
        srs = osr.SpatialReference()
        srs.ImportFromProj4(Region.t_srs)
        mapds.SetProjection(srs.ExportToWkt())

        # modify elarray and save it as raster band 2
        actualel = ((elarray - self.trim)/self.vscale)+self.sealevel
        mapds.GetRasterBand(Region.rasters['elevation']).WriteArray(actualel)
        elarray = None
        actualel = None

        # generate crust and save it as raster band 4
        newcrust = Crust(mapds.RasterXSize, mapds.RasterYSize, wantCL=wantCL)
        crustarray = newcrust()
        mapds.GetRasterBand(Region.rasters['crust']).WriteArray(crustarray)
        crustarray = None
        newcrust = None

        # read landcover array
        lcvrt = os.path.join(self.mapsdir, '%s.vrt' % (self.lclayer)) 
        lcfile = os.path.join(self.mapsdir, '%s.tif' % (self.lclayer))
        # here are the things that need to happen
        lcextents = self.albersextents['landcover']

        # if True, use new code, if False, use gdalwarp
        if True:
            # 1. the new file must be read into an array and flattened
            vrtds = gdal.Open(lcvrt, GA_ReadOnly)
            vrtgeotrans = vrtds.GetGeoTransform()
            vrtband = vrtds.GetRasterBand(1)
            values = vrtband.ReadAsArray(0, 0, vrtds.RasterXSize, vrtds.RasterYSize)
            # nodata is treated as water, which is 11
            vrtnodata = vrtband.GetNoDataValue()
            if (vrtnodata == None):
                vrtnodata = 0
            values[values == vrtnodata] = 11
            values = values.flatten()
            vrtband = None
            # 2. a new array of original scale coordinates must be created
            vrtxrange = [vrtgeotrans[0] + vrtgeotrans[1] * x for x in xrange(vrtds.RasterXSize)]
            vrtyrange = [vrtgeotrans[3] + vrtgeotrans[5] * y for y in xrange(vrtds.RasterYSize)]
            vrtds = None
            coords = numpy.array([(x, y) for y in vrtyrange for x in vrtxrange])
            # 3. a new array of goal scale coordinates must be made
            # landcover extents are used for the bathy depth array
            # yes, it's confusing.  sorry.
            depthxlen = int((lcextents['xmax']-lcextents['xmin'])/self.scale)
            depthylen = int((lcextents['ymax']-lcextents['ymin'])/self.scale)
            depthxrange = [lcextents['xmin'] + self.scale * x for x in xrange(depthxlen)]
            depthyrange = [lcextents['ymax'] - self.scale * y for y in xrange(depthylen)]
            depthbase = numpy.array([(x, y) for y in depthyrange for x in depthxrange])
            # 4. an inverse distance tree must be built from that
            lcCLIDT = CLIDT(coords, values, depthbase, wantCL=wantCL)
            # 5. the desired output comes from that inverse distance tree
            deptharray = lcCLIDT()
            deptharray.resize((depthylen, depthxlen))
            lcCLIDT = None
        else:
            warpcmd = 'gdalwarp -q -multi -t_srs "%s" -tr %d %d -te %d %d %d %d -r near %s %s' % (Region.t_srs, self.scale, self.scale, lcextents['xmin'], lcextents['ymin'], lcextents['xmax'], lcextents['ymax'], lcvrt, lcfile)

            try:
                os.remove(lcfile)
            except OSError:
                pass
            # NB: make this work on Windows too!
            os.system("%s" % warpcmd)
            lcds = gdal.Open(lcfile, GA_ReadOnly)
            lcband = lcds.GetRasterBand(1)
            # depth array is entire landcover region, landcover array is subset
            deptharray = lcband.ReadAsArray(0, 0, lcds.RasterXSize, lcds.RasterYSize)
        lcarray = deptharray[self.maxdepth:-1*self.maxdepth, self.maxdepth:-1*self.maxdepth]
        geotrans = [ lcextents['xmin'], self.scale, 0, lcextents['ymax'], 0, -1 * self.scale ]
        projection = srs.ExportToWkt()
        bathyarray = getBathy(deptharray, self.maxdepth, geotrans, projection)
        mapds.GetRasterBand(Region.rasters['bathy']).WriteArray(bathyarray)
        # perform terrain translation
        # NB: figure out why this doesn't work up above
        lcpid = self.lclayer[:3]
        if lcpid in Terrain.translate:
            trans = Terrain.translate[lcpid]
            for key in trans:
                lcarray[lcarray == key] = 1000+trans[key]
            lcarray[lcarray > 1000] -= 1000
            for value in numpy.unique(lcarray).flat:
                if value not in Terrain.terdict:
                    print "bad value: ", value
        mapds.GetRasterBand(Region.rasters['landcover']).WriteArray(lcarray)

        # close the dataset
        mapds = None
