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

import newcoords
import invdisttree
from newutils import cleanmkdir, ds

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

    # sadness
    zipfileBroken = False

    # default values
    tilesize = 256
    scale = 6
    # product types in order of preference
    landcoverIDs = ['L07', 'L04', 'L01', 'L92', 'L6L']
    elevationIDs = ['ND9', 'ND3', 'NED', 'NAK']
    #elevationIDs = ['ND3', 'NED', 'NAK', 'ND9']

    def __init__(self, name, xmax, xmin, ymax, ymin, tilesize=None, scale=None, lcIDs=None, elIDs=None, debug=False):
        """Create a region based on lat-longs and other parameters."""
        # NB: smart people check names
        self.name = name

        if tilesize == None:
            tilesize = Region.tilesize
        else:
            if (tilesize % 16 != 0):
                raise AttributeError, 'bad tilesize %s' % tilesize
        self.tilesize = tilesize

        if scale == None:
            scale = Region.scale
        else:
            if (30 % scale != 0):
                raise AttributeError, 'bad scale %s' % scale
        self.scale = scale
        self.mult = 30 / scale

        # specified IDs must be in region list
        if lcIDs == None:
            landcoverIDs = Region.landcoverIDs
        else:
            landcoverIDs = [ ID for ID in lcIDs if ID in Region.landcoverIDs ]
            if landcoverIDs == []:
                raise AttributeError, 'invalid landcover ID'

        if elIDs == None:
            elevationIDs = Region.elevationIDs
        else:
            elevationIDs = [ ID for ID in elIDs if ID in Region.elevationIDs ]
            if elevationIDs == []:
                raise AttributeError, 'invalid elevation ID'

        # crazy directory fun
        self.regiondir = os.path.join('Regions', self.name)
        cleanmkdir(self.regiondir)

        self.mapsdir = os.path.join('Datasets', self.name)
        cleanmkdir(self.mapsdir)

        # these are the latlong values
        llxmax = max(xmax, xmin)
        llxmin = min(xmax, xmin)
        llymax = max(ymax, ymin)
        llymin = min(ymax, ymin)

        # access the web service
        # NB: raise hell if it is inaccessible
        wsdlConv = "http://extract.cr.usgs.gov/XMLWebServices/Coordinate_Conversion_Service.asmx?WSDL"
        clientConv = suds.client.Client(wsdlConv)
        # This web service returns suds.sax.text.Text not XML sigh
        Convre = "<X Coordinate>(.*?)</X Coordinate > <Y Coordinate>(.*?)</Y Coordinate >"

        # convert from WGS84 to Albers
        ULdict = {'X_Value': llxmin, 'Y_Value': llymin, 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        URdict = {'X_Value': llxmax, 'Y_Value': llymin, 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        LLdict = {'X_Value': llxmin, 'Y_Value': llymax, 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        LRdict = {'X_Value': llxmax, 'Y_Value': llymax, 'Current_Coordinate_System': Region.wgs84, 'Target_Coordinate_System': Region.albers}
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
        self.txmax = int(ceil(mxmax / realsize))
        self.tymax = int(ceil(mymax / realsize))
        self.txmin = int(floor(mxmin / realsize))
        self.tymin = int(floor(mymin / realsize))

        # add border
        # NB: this is ideal but not what's transmitted
        # should be albersxmax maybe?  mcxmax?
        lcxmax = ((self.txmax + 1) * realsize)
        lcxmin = ((self.txmin - 1) * realsize)
        lcymax = ((self.tymax + 1) * realsize)
        lcymin = ((self.tymin - 1) * realsize)

        # now convert back from Albers to WGS84
        ULdict = {'X_Value': lcxmin, 'Y_Value': lcymin, 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        URdict = {'X_Value': lcxmax, 'Y_Value': lcymin, 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        LLdict = {'X_Value': lcxmin, 'Y_Value': lcymax, 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        LRdict = {'X_Value': lcxmax, 'Y_Value': lcymax, 'Current_Coordinate_System': Region.albers, 'Target_Coordinate_System': Region.wgs84}
        (LRx, LRy) = re.findall(Convre, clientConv.service.getCoordinates(**LRdict))[0]

        # select maximum values for elevation extents
        xfloat = [float(x) for x in [ULx, URx, LLx, LRx]]
        yfloat = [float(y) for y in [ULy, URy, LLy, LRy]]
        # NB: these are what's used for both!
        self.mapxmax = max(xfloat)
        self.mapxmin = min(xfloat)
        self.mapymax = max(yfloat)
        self.mapymin = min(yfloat)

        # check availability of product IDs and identify specific layer IDs
        self.lclayer = self.checkavail(landcoverIDs)
        self.ellayer = self.checkavail(elevationIDs)

        # write the values to the file
        stream = file(os.path.join(self.regiondir, 'Region.yaml'), 'w')
        yaml.dump(self, stream)
        stream.close()

    @staticmethod
    def decodeLayerID(layerID):
        """Given a layer ID, return the product type, image type, metadata type, and compression type."""
        # NB: convert this to dicts
        productID = layerID[0]+layerID[1]+layerID[2]
        if (productID in Region.landcoverIDs):
            pType = "landcover"
        elif (productID in Region.elevationIDs):
            pType = "elevation"
        else:
            raise AttributeError, 'Invalid productID %s' % productID

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
            raise AttributeError, 'Invalid imagetype %s' % imagetype
        
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
            raise AttributeError, 'Invalid metatype %s' % metatype

        compressiontype = layerID[6]
        if (compressiontype == "T"):
            cType = "TGZ"
        elif (compressiontype == "Z"):
            cType = "ZIP"
        else:
            raise AttributeError, 'Invalid compressiontype %s' % compressiontype
        
        return (pType, iType, mType, cType)

    def mapfile(self, layer):
        """Generate map file based on layer"""
        return os.path.join(self.mapsdir, layer, '%s.%s' % (layer, Region.decodeLayerID(layer)[1]))

    def checkavail(self, productlist):
        """Check availability with web service."""
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
        rAdict = {'Attribs': ','.join(attributes), 'XMin': self.mapxmin, 'XMax': self.mapxmax, 'YMin': self.mapymin, 'YMax': self.mapymax, 'EPSG': Region.wgs84}
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
            xmlString = "<REQUEST_SERVICE_INPUT><AOI_GEOMETRY><EXTENT><TOP>%f</TOP><BOTTOM>%f</BOTTOM><LEFT>%f</LEFT><RIGHT>%f</RIGHT></EXTENT><SPATIALREFERENCE_WKID/></AOI_GEOMETRY><LAYER_INFORMATION><LAYER_IDS>%s</LAYER_IDS></LAYER_INFORMATION><CHUNK_SIZE>%d</CHUNK_SIZE><JSON></JSON></REQUEST_SERVICE_INPUT>" % (self.mapymax, self.mapymin, self.mapxmin, self.mapxmax, layerID, 250) # can be 100, 15, 25, 50, 75, 250

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
        (pType, iType, mType, cType) = Region.decodeLayerID(layerID)
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
            (pType, iType, mType, cType) = Region.decodeLayerID(layerID)
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
                    if (cType == "TGZ"):
                        cFile = tarfile.open(fullfile)
                    elif (cType == "ZIP"):
                        cFile = zipfile.ZipFile(fullfile)
                    cFile.extract(compimage, layerdir)
                    cFile.close()
                else:
                    if (cType == "TGZ"):
                        cFile = tarfile.open(fullfile)
                        cFile.extract(compimage, layerdir)
                    elif (cType == "ZIP"):
                        omfgcompimage = "\\".join([compbase, "%s.%s" % (compbase, iType)])
                        os.mkdir(os.path.dirname(os.path.join(datasubdir,compimage)))
                        cFile = zipfile.ZipFile(fullfile)
                        cFile.extract(omfgcompimage, datasubdir)
                        os.rename(os.path.join(datasubdir,omfgcompimage),os.path.join(layerdir,compimage))
                    cFile.close()
            os.system("cd %s && gdalbuildvrt -resolution highest %s.vrt */*.%s >/dev/null && gdal_translate %s.vrt %s.%s >/dev/null" % (layerdir, layerID, iType, layerID, layerID, iType))

    def warpelevation(self):
        """Warp elevation file to match landcover file."""
        lcimage = self.mapfile(self.lclayer)
        elimage = self.mapfile(self.ellayer)
        elimageorig = "%s-orig" % elimage
        os.rename(elimage, elimageorig)
        prffd = NamedTemporaryFile(delete=False)
        prfname = prffd.name
        prffd.close()
        os.system('gdalinfo %s | sed -e "1,/Coordinate System is:/d" -e "/Origin =/,\$d" | xargs echo > %s' % (lcimage, prfname))
        os.system('gdalwarp -srcnodata -340282346638528859811704183484516925440.000 -dstnodata 0 -t_srs %s -r cubic %s %s >/dev/null' % (prfname, elimageorig, elimage))
        os.remove(prfname)

    def getfiles(self):
        """Get files from USGS."""
        layerIDs = [self.lclayer, self.ellayer]
        downloadURLs = self.requestvalidation(layerIDs)
        for layerID in downloadURLs.keys():
            for downloadURL in downloadURLs[layerID]:
                self.downloadfile(layerID, downloadURL)
        self.extractfiles()
        self.warpelevation()
        
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
        assert os.path.exists(elimageorig), 'getfiles: elimageorig %s does not exist' % elimageorig
    except AssertionError, e:
        print 'getfiles check failed:', e
    else:
        print 'getfiles check passed'

if __name__ == '__main__':
    checkRegion();
