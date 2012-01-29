#!/usr/bin/env python

from __future__ import division
from math import ceil, floor
import suds
import re
import os
import urllib2
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import logging
logging.basicConfig(level=logging.INFO)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)
from time import sleep
from tempfile import NamedTemporaryFile
import zipfile
import tarfile
from newutils import cleanmkdir, ds
import sys
sys.path.append('..')
from pymclevel import mclevel

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
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
    
    # sadness
    zipfileBroken = False

    # default values
    tilesize = 256
    scale = 6
    vscale = 6
    trim = 0
    sealevel = 64
    maxdepth = 32

    # tileheight is height of map in Minecraft units (128, sigh)
    tileheight = mclevel.MCInfdevOldLevel.Height
    # headroom is room between top of terrain and top of map
    headroom = 16

    # product types in order of preference
    productIDs = { 'elevation': ['ND9', 'ND3', 'NED', 'NAK'],
                   'landcover': ['L07', 'L04', 'L01', 'L92', 'L6L']}

    # nodata values
    nodatavals = { 'elevation': [-340282346638528859811704183484516925440, 0],
                   'landcover': [255, 11] }

    # image types
    # NB: only tif is known to work here
    imageTypes = { 'tif': ['02'],
                   'arc': ['01'],
                   'bil': ['03'],
                   'GridFloat': ['05'],
                   'IMG': ['12'],
                   'bil_16int': ['15'] }

    # meta types
    # NB: currently ignored
    metaTypes = { 'ALL': ['A'],
                  'FAQ': ['F'],
                  'HTML': ['H'],
                  'SGML': ['S'],
                  'TXT': ['T'],
                  'XML': ['X'] }

    # compression types
    # NB: zipfile module broken so tgz recommended
    compressionTypes = { 'tgz': ['T'],
                         'zip': ['Z'] }

    def __init__(self, name, xmax, xmin, ymax, ymin, tilesize=None, scale=None, vscale=None, trim=None, sealevel=None, maxdepth=None, lcIDs=None, elIDs=None, debug=False):
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

        # sealevel 
        if sealevel == None:
            sealevel = Region.sealevel
        else:
            minsealevel = 2
            maxsealevel = Region.tileheight - Region.headroom
            self.sealevel = min(max(sealevel, minsealevel), maxsealevel)

        # maxdepth depends upon sealevel
        if maxdepth == None:
            maxdepth = Region.maxdepth
        else:
            minmaxdepth = 1
            maxmaxdepth = self.sealevel - 1
            self.maxdepth = min(max(maxdepth, minmaxdepth), maxmaxdepth)

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
        if (scale > 5):
            self.productIDs['elevation'].remove('ND9')
        if (scale > 15):
            self.productIDs['elevation'].remove('ND3')

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

        # crazy directory fun
        self.regiondir = os.path.join('Regions', self.name)
        cleanmkdir(self.regiondir)

        self.mapsdir = os.path.join('Regions', self.name, 'Datasets')
        cleanmkdir(self.mapsdir)

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

        # write yaml file
        self.writeyaml()

    def writeyaml(self):
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

    def mapfile(self, layer):
        """Generate map file based on layer"""
        return os.path.join(self.mapsdir, layer, '%s.%s' % (layer, self.decodeLayerID(layer)[1]))

    def checkavail(self, productlist, maptype):
        """Check availability with web service."""
        mapextents = self.wgs84extents[maptype]

        # access the web service to check availability
        wsdlInv = "http://ags.cr.usgs.gov/index_service/Index_Service_SOAP.asmx?WSDL"
        clientInv = suds.client.Client(wsdlInv)

        # ensure desired attributes are present
        desiredAttributes = ['PRODUCTKEY']
        attributes = []
        attributeList = clientInv.service.return_Attribute_List()
        for attribute in desiredAttributes:
            if attribute in attributeList[0]:
                attributes.append(attribute)
        if len(attributes) == 0:
            raise AttributeError, "No attributes found"
    
        # return_attributes arguments dictionary
        rAdict = {'Attribs': ','.join(attributes), 'XMin': mapextents['xmin'], 'XMax': mapextents['xmax'], 'YMin': mapextents['ymin'], 'YMax': mapextents['ymax'], 'EPSG': Region.wgs84}
        rAatts = clientInv.service.return_Attributes(**rAdict)
        # store offered products in a list
        offered = []
        # this returns an array of custom attributes
        # each element of the array has a key-value pair
        # in our case, there's only one key: PRODUCTKEY
        for elem in rAatts.ArrayOfCustomAttributes:
            for each in elem[0]:
                if (each[0] == 'PRODUCTKEY' and each[1] in productlist):
                        offered.append(each[1])
        # this should extract the first
        try:
            productID = [ ID for ID in productlist if ID in offered ][0]
        except IndexError:
            raise AttributeError, "No products are available for this location!"
        # check download options
        # NB: integrate with new types seen above
        OFgood = [u'GeoTIFF']
        MFgood = [u'HTML', u'ALL', u'FAQ', u'SGML', u'TXT', u'XML']
        CFgood = [u'TGZ', u'ZIP']
        wsdlInv = "http://ags.cr.usgs.gov/index_service/Index_Service_SOAP.asmx?WSDL"
        clientInv = suds.client.Client(wsdlInv)
        productdict = {'ProductIDs': productID}
        doproducts = clientInv.service.return_Download_Options(**productdict)
        [doPID, doType, doOF, doCF, doMF] = [value for (key, value) in doproducts['DownloadOptions'][0]]
        # assemble layerID
        layerID = doPID
        OFdict = dict([reversed(pair.split('-')) for pair in doOF.split(',')])
        CFdict = dict([reversed(pair.split('-')) for pair in doCF.split(',')])
        MFdict = dict([reversed(pair.split('-')) for pair in doMF.split(',')])
        OFfound = [OFdict[OFval] for OFval in OFgood if OFval in OFdict]
        if OFfound:
            layerID += OFfound[0]
        else:
            raise AttributeError, 'no acceptable output format found'
        MFfound = [MFdict[MFval] for MFval in MFgood if MFval in MFdict]
        if MFfound:
            layerID += MFfound[0]
        else:
            raise AttributeError, 'no acceptable metadata format found'
        CFfound = [CFdict[CFval] for CFval in CFgood if CFval in CFdict]
        if CFfound:
            layerID += CFfound[0]
        else:
            raise AttributeError, 'no acceptable compression format found'
        return str(layerID)

    def requestvalidation(self, layerIDs):
        """Generates download URLs from layer IDs."""
        retval = {}

        # request validation
        wsdlRequest = "http://extract.cr.usgs.gov/requestValidationService/wsdl/RequestValidationService.wsdl"
        clientRequest = suds.client.Client(wsdlRequest)

        # we now iterate through layerIDs
        for layerID in layerIDs:
            (pType, iType, mType, cType) = self.decodeLayerID(layerID)
            mapextents = self.wgs84extents[pType]
            xmlString = "<REQUEST_SERVICE_INPUT><AOI_GEOMETRY><EXTENT><TOP>%f</TOP><BOTTOM>%f</BOTTOM><LEFT>%f</LEFT><RIGHT>%f</RIGHT></EXTENT><SPATIALREFERENCE_WKID/></AOI_GEOMETRY><LAYER_INFORMATION><LAYER_IDS>%s</LAYER_IDS></LAYER_INFORMATION><CHUNK_SIZE>%d</CHUNK_SIZE><JSON></JSON></REQUEST_SERVICE_INPUT>" % (mapextents['ymax'], mapextents['ymin'], mapextents['xmin'], mapextents['xmax'], layerID, 250) # can be 100, 15, 25, 50, 75, 250

            response = clientRequest.service.processAOI2(xmlString)

            print "Requested URLs for layer ID %s..." % layerID

            # I am still a bad man.
            downloadURLs = [x.rsplit("</DOWNLOAD_URL>")[0] for x in response.split("<DOWNLOAD_URL>")[1:]]

            retval[layerID] = downloadURLs

        return retval

    def downloadfile(self, layerID, downloadURL):
        """Actually download the file at the URL."""
        # FIXME: extract try/expect around urlopen
        # FIXME: consider breaking apart further
        (pType, iType, mType, cType) = self.decodeLayerID(layerID)
        layerdir = os.path.join(self.mapsdir, layerID)
        cleanmkdir(layerdir)

        print "  Requesting download for %s." % layerID
        # initiateDownload and get the response code
        # put _this_ in its own function!
        try:
            page = urllib2.urlopen(downloadURL.replace(' ','%20'))
        except IOError, e:
            if hasattr(e, 'reason'):
                raise IOError, e.reason
            elif hasattr(e, 'code'):
                raise IOError, e.code
            else:
                raise IOError
        else:
            result = page.read()
            page.close()
            # parse response for request id
            if result.find("VALID>false") > -1:
                # problem with initiateDownload request string
                # handle that here
                pass
            else:
                # downloadRequest successfully entered into queue
                startPos = result.find("<ns:return>") + 11
                endPos = result.find("</ns:return>")
                requestID = result[startPos:endPos]
        print "  request ID is %s" % requestID

        downloadDict = {'downloadID': requestID}
        sleep(5)
        while True:
            dsPage = urllib2.urlopen("http://extract.cr.usgs.gov/axis2/services/DownloadService/getDownloadStatus?downloadID=%s" % requestID)
            result = dsPage.read()
            dsPage.close()
            result = result.replace("&#xd;\n"," ")
            # parse out status code and status text
            startPos = result.find("<ns:return>") + 11
            endPos = result.find("</ns:return>")
            (code, status) = result[startPos:endPos].split(',',1)
            print "  status is %s" % status
            if (int(code) == 400):
                break
            sleep(15)

        getFileURL = "http://extract.cr.usgs.gov/axis2/services/DownloadService/getData?downloadID=%s" % requestID
        try:
            page3 = urllib2.Request(getFileURL)
            opener = urllib2.build_opener(SmartRedirectHandler())
            obj = opener.open(page3)
            location = obj.headers['Location'] 
            filename = location.split('/')[-1].split('#')[0].split('?')[0]        
        except IOError, e:
            if hasattr(e, 'reason'):
                raise IOError, e.reason
            elif hasattr(e, 'code'):
                raise IOError, e.code
            else:
                raise IOError
        else:
            print "  downloading %s now!" % filename
            downloadFile = open(os.path.join(layerdir,filename), 'wb')
            while True:
                data = obj.read(8192)
                if data == "":
                    break
                downloadFile.write(data)
            downloadFile.close()
            obj.close()

        # UGH
        setStatusURL = "http://extract.cr.usgs.gov/axis2/services/DownloadService/setDownloadComplete?downloadID=%s" % requestID
        try:
            page4 = urllib2.urlopen(setStatusURL)
        except IOError, e:
            if hasattr(e, 'reason'):
                raise IOError, e.reason
            elif hasattr(e, 'code'):
                raise IOError, e.code
            else:
                raise IOError
        else:
            result = page4.read()
            page4.close()
            # remove carriage returns
            result = result.replace("&#xd;\n"," ")
            # parse out status code and status text
            startPos = result.find("<ns:return>") + 11
            endPos = result.find("</ns:return>")
            status = result[startPos:endPos]

    def extractfiles(self):
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
                compimage = os.path.join(compbase, "%s.%s" % (compbase, iType))
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
                        omfgcompimage = "\\".join([compbase, "%s.%s" % (compbase, iType)])
                        os.mkdir(os.path.dirname(os.path.join(datasubdir,compimage)))
                        cFile = zipfile.ZipFile(fullfile)
                        cFile.extract(omfgcompimage, datasubdir)
                        os.rename(os.path.join(datasubdir,omfgcompimage),os.path.join(layerdir,compimage))
                    cFile.close()
            vrtfile = '%s.vrt' % layerID
            imagefile = '%s.%s' % (layerID, iType)
            buildvrtcmd = 'gdalbuildvrt -resolution highest %s */*.%s >/dev/null' % (vrtfile, iType)
            # NB: possibly do vscale here with gdal_translate!
            mapextents = self.albersextents[pType]
            (srcnodata, dstnodata) = Region.nodatavals[pType]
            warpcmd = 'gdalwarp -q -multi -t_srs "%s" -tr %d %d -te %d %d %d %d -srcnodata %d -dstnodata %d %s %s' % (Region.t_srs, self.scale, self.scale, mapextents['xmin'], mapextents['ymin'], mapextents['xmax'], mapextents['ymax'], srcnodata, dstnodata, vrtfile, imagefile)
            os.system('cd %s && %s && %s' % (layerdir, buildvrtcmd, warpcmd))

    def getfiles(self):
        """Get files from USGS."""
        layerIDs = [self.lclayer, self.ellayer]
        downloadURLs = self.requestvalidation(layerIDs)
        for layerID in downloadURLs.keys():
            for downloadURL in downloadURLs[layerID]:
                self.downloadfile(layerID, downloadURL)
        self.extractfiles()

        # update trim and vscale
        elds = ds(self.mapfile(self.ellayer))
        elband = elds.GetRasterBand(1)
        elmin = elband.GetMinimum()
        elmax = elband.GetMaximum()
        if elmin is None or elmax is None:
            (elmin, elmax) = elband.ComputeRasterMinMax(False)
        elmin = int(elmin)
        elmax = int(elmax)

        # trim depends upon minelev
        mintrim = Region.trim
	# what if the minimum elevation is below sea level?!
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

        # write yaml file
        self.writeyaml()
        
def checkRegion():
    epsilon = 0.000001 # comparing floating point with equals is wrong

    try:
        Test2 = Region(name='Test2', ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332, tilesize=255)
    except AttributeError, e:
        print 'Tilesize check passed: ', e
    else:
        raise AssertionError, 'Mod 16 check failed'

    try:
        Test2 = Region(name='Test2', ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332, scale=7)
    except AttributeError, e:
        print 'Scale check passed: ', e
    else:
        raise AssertionError, 'Scale check failed'

    try:
        Test2 = Region(name='Test2', ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332, elIDs=['ND4'])
    except AttributeError, e:
        print 'Elevation ID check passed: ', e
    else:
        raise AssertionError, 'Elevation ID check failed'

    try:
    	Test2 = Region(name='Test2', ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332)
    except AssertionError, e:
        print 'Region creation failed: ', e
    else:
        print 'Region creation passed'

    yamlfile = file(os.path.join('Regions', 'Test', 'Region.yaml'))
    myyaml = yaml.load(yamlfile)
    yamlfile.close()
    try:
        assert myyaml.tilesize == Test2.tilesize, 'YAML tilesize does not match'
        assert myyaml.scale == Test2.scale, 'YAML scale does not match'
        assert (myyaml.mapxmax - Test2.mapxmax) < epsilon, 'YAML mapxmax does not match'
        assert (myyaml.mapxmin - Test2.mapxmin) < epsilon, 'YAML mapxmin does not match'
        assert (myyaml.mapymax - Test2.mapymax) < epsilon, 'YAML mapymax does not match'
        assert (myyaml.mapymin - Test2.mapymin) < epsilon, 'YAML mapymin does not match'
        assert myyaml.txmax == Test2.txmax, 'YAML txmax does not match'
        assert myyaml.txmin == Test2.txmin, 'YAML txmin does not match'
        assert myyaml.tymax == Test2.tymax, 'YAML tymax does not match'
        assert myyaml.tymin == Test2.tymin, 'YAML tymin does not match'
        assert myyaml.lclayer == Test2.lclayer, 'YAML lclayer does not match'
        assert myyaml.ellayer == Test2.ellayer, 'YAML ellayer does not match'
    except AssertionError, e:
        print 'YAML check failed: ', e
    else:
        print 'YAML check passed'
 
    Test2.getfiles()
    try:
        # for now, just check existence of all three map files
        lcimage = Test2.mapfile(Test2.lclayer)
        elimage = Test2.mapfile(Test2.ellayer)
        elimageorig = '%s-orig' % elimage
        assert os.path.exists(lcimage), 'getfiles: lcimage %s does not exist' % lcimage
        assert os.path.exists(elimage), 'getfiles: elimage %s does not exist' % elimage
    except AssertionError, e:
        print 'getfiles check failed:', e
    else:
        print 'getfiles check passed'

if __name__ == '__main__':
    checkRegion();
