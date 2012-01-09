from __future__ import division
from math import ceil, floor
import suds
import re
import os
import shutil
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
from dataset import decodeLayerID, landcoverIDs, elevationIDs, warpFile
import zipfile
import tarfile

# sadness
zipfileBroken = False

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


    def __init__(self, name, xmax, xmin, ymax, ymin, tilesize=256, scale=6, maxdepth=16):
        """Create a region based on lat-longs and other parameters."""
        # NB: smart people check names
        self.name = name
        if (tilesize % 16 != 0):
            raise AttributeError
        self.tilesize = tilesize
        self.scale = scale
        self.maxdepth = maxdepth

        # crazy directory fun
        regiondir = os.path.join('Regions', self.name)
        self.mapsdir = os.path.join(regiondir, 'Maps')
        if os.path.isdir(regiondir):
            shutil.rmtree(regiondir)
        if not os.path.exists(regiondir):
            os.makedirs(self.mapsdir)
        else:
            raise IOError, '%s already exists' % regiondir

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
        ULdict = {'X_Value': llxmin, 'Y_Value': llymin, 'Current_Coordinate_System': self.wgs84, 'Target_Coordinate_System': self.albers}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        URdict = {'X_Value': llxmax, 'Y_Value': llymin, 'Current_Coordinate_System': self.wgs84, 'Target_Coordinate_System': self.albers}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        LLdict = {'X_Value': llxmin, 'Y_Value': llymax, 'Current_Coordinate_System': self.wgs84, 'Target_Coordinate_System': self.albers}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        LRdict = {'X_Value': llxmax, 'Y_Value': llymax, 'Current_Coordinate_System': self.wgs84, 'Target_Coordinate_System': self.albers}
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
        lcxmax = (self.txmax * realsize) + self.maxdepth
        lcxmin = (self.txmin * realsize) - self.maxdepth
        lcymax = (self.tymax * realsize) + self.maxdepth
        lcymin = (self.tymin * realsize) - self.maxdepth

        # now convert back from Albers to WGS84
        ULdict = {'X_Value': lcxmin, 'Y_Value': lcymin, 'Current_Coordinate_System': self.albers, 'Target_Coordinate_System': self.wgs84}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        URdict = {'X_Value': lcxmax, 'Y_Value': lcymin, 'Current_Coordinate_System': self.albers, 'Target_Coordinate_System': self.wgs84}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        LLdict = {'X_Value': lcxmin, 'Y_Value': lcymax, 'Current_Coordinate_System': self.albers, 'Target_Coordinate_System': self.wgs84}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        LRdict = {'X_Value': lcxmax, 'Y_Value': lcymax, 'Current_Coordinate_System': self.albers, 'Target_Coordinate_System': self.wgs84}
        (LRx, LRy) = re.findall(Convre, clientConv.service.getCoordinates(**LRdict))[0]

        # select maximum values for elevation extents
        xfloat = [float(x) for x in [ULx, URx, LLx, LRx]]
        yfloat = [float(y) for y in [ULy, URy, LLy, LRy]]
        # NB: these are what's used for both!
        self.mapxmax = max(xfloat)
        self.mapxmin = min(xfloat)
        self.mapymax = max(yfloat)
        self.mapymin = min(yfloat)

        # write the values to the file
        stream = file(os.path.join(regiondir, 'Region.yaml'), 'w')
        yaml.dump({'tilesize': self.tilesize, 
                   'scale': self.scale, 
                   'maxdepth': self.maxdepth,
                   'mapxmax': self.mapxmax,
                   'mapxmin': self.mapxmin,
                   'mapymax': self.mapymax,
                   'mapymin': self.mapymin,
                   'txmax': self.txmax,
                   'txmin': self.txmin,
                   'tymax': self.tymax,
                   'tymin': self.tymin,
                   }, 
                  stream)
        stream.close()

    def checkavail(self, xmin, xmax, ymin, ymax, productlist, epsg=4326):
        """Check availability with web service."""
        # access the web service to check availability
        wsdlInv = "http://ags.cr.usgs.gov/index_service/Index_Service_SOAP.asmx?WSDL"
        clientInv = suds.client.Client(wsdlInv)

        # ensure desired attributes are present
        desiredAttributes = ['PRODUCTKEY', 'SEAMTITLE']
        attributes = []
        attributeList = clientInv.service.return_Attribute_List()
        for attribute in desiredAttributes:
            if attribute in attributeList[0]:
                attributes.append(attribute)
        if len(attributes) == 0:
            raise AttributeError, "No attributes found"
    
        # return_attributes arguments dictionary
        rAdict = {'Attribs': ','.join(attributes), 'XMin': xmin, 'XMax': xmax, 'YMin': ymin, 'YMax': ymax, 'EPSG': epsg}
        rAatts = clientInv.service.return_Attributes(**rAdict)
        # store offered products in a list
        offered = []
        # this returns an array of custom attributes
        # each element of the array has a key-value pair
        # in our case, there's only one key: PRODUCTKEY
        for elem in rAatts.ArrayOfCustomAttributes:
            for each in elem[0]:
                if (each[0] == 'PRODUCTKEY'):
                    if (each[1] in productlist):
                        offered.append(each[1])
        # this should extract the first
        for ID in productlist:
            if (ID in offered):
                return [ID, xmin, xmax, ymin, ymax]
        raise AttributeError, "No products are available for this location!"

    def checkdownloadoptions(self, productIDs):
        """Check download options for product IDs."""
        wsdlInv = "http://ags.cr.usgs.gov/index_service/Index_Service_SOAP.asmx?WSDL"
        clientInv = suds.client.Client(wsdlInv)
        productdict = {'ProductIDs': ','.join([elem[0] for elem in productIDs])}
        doproducts = clientInv.service.return_Download_Options(**productdict)
        layerIDs = []
        for products in doproducts[0]:
            productID = products[0]
            for ID in productIDs:
                if (productID == ID[0]):
                    xmin = ID[1]
                    xmax = ID[2]
                    ymin = ID[3]
                    ymax = ID[4]
            layerID = productID
            outputformats = {}
            compressionformats = {}
            metadataformats = {}
            for pair in products[2].split(','):
                (v, k) = pair.split('-')
                outputformats[k] = v
            for pair in products[3].split(','):
                (v, k) = pair.split('-')
                compressionformats[k] = v
            for pair in products[4].split(','):
                (v, k) = pair.split('-')
                metadataformats[k] = v
            # I want GeoTIFF, HTML and TGZ here
            if u'GeoTIFF' in outputformats:
                layerID += outputformats['GeoTIFF']
            else:
                raise AttributeError, 'GeoTIFF not available'
            # I do not use metadata so I don't care!
            if u'HTML' in metadataformats:
                layerID += metadataformats['HTML']
            elif u'ALL' in metadataformats:
                layerID += metadataformats['ALL']
            elif u'FAQ' in metadataformats:
                layerID += metadataformats['FAQ']
            elif u'SGML' in metadataformats:
                layerID += metadataformats['SGML']
            elif u'TXT' in metadataformats:
                layerID += metadataformats['TXT']
            elif u'XML' in metadataformats:
                layerID += metadataformats['XML']
            else:
                raise AttributeError, 'HTML not available'
            # prefer TGZ to ZIP
            # consider preferences like landcoverIDs
            if u'TGZ' in compressionformats:
                layerID += compressionformats['TGZ']
            elif u'ZIP' in compressionformats:
                layerID += compressionformats['ZIP']
            else:
                raise AttributeError, 'no compression formats available'
            layerIDs.append([layerID, xmin, xmax, ymin, ymax])
        return layerIDs

    def requestvalidation(self, layerIDs):
        """Generates download URLs from layer IDs."""
        retval = {}

        # request validation
        wsdlRequest = "http://extract.cr.usgs.gov/requestValidationService/wsdl/RequestValidationService.wsdl"
        clientRequest = suds.client.Client(wsdlRequest)

        # we now iterate through layerIDs
        for layerID in layerIDs:
            (tag, xmin, xmax, ymin, ymax) = layerID
            xmlString = "<REQUEST_SERVICE_INPUT><AOI_GEOMETRY><EXTENT><TOP>%f</TOP><BOTTOM>%f</BOTTOM><LEFT>%f</LEFT><RIGHT>%f</RIGHT></EXTENT><SPATIALREFERENCE_WKID/></AOI_GEOMETRY><LAYER_INFORMATION><LAYER_IDS>%s</LAYER_IDS></LAYER_INFORMATION><CHUNK_SIZE>%d</CHUNK_SIZE><JSON></JSON></REQUEST_SERVICE_INPUT>" % (ymax, ymin, xmin, xmax, tag, 250) # can be 100, 15, 25, 50, 75, 250

            response = clientRequest.service.processAOI2(xmlString)

            #print "Requested URLs for layer ID %s..." % tag

            # I am still a bad man.
            downloadURLs = [x.rsplit("</DOWNLOAD_URL>")[0] for x in response.split("<DOWNLOAD_URL>")[1:]]

            retval[tag] = downloadURLs

        return retval

    def downloadfile(self, layerID, downloadURL):
        """Actually download the file at the URL."""
        # FIXME: extract try/expect around urlopen
        # FIXME: consider breaking apart further
        layerdir = os.path.join(self.mapsdir, layerID)
        if not os.path.exists(layerdir):
            os.makedirs(layerdir)

        #print "  Requesting download for %s." % layerID
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
        #print "  request ID is %s" % requestID

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
            #print "  status is %s" % status
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
            #print "  downloading %s now!" % filename
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
        for layerID in layerIDs:
            (pType, iType, mType, cType) = decodeLayerID(layerID)
            filesuffix = cType.lower()
            layersubdir = os.path.join(self.mapsdir, layerID)
            compfiles = [ name for name in os.listdir(layersubdir) if (os.path.isfile(os.path.join(layersubdir, name)) and name.endswith(filesuffix)) ]
            for compfile in compfiles:
                (compbase, compext) = os.path.splitext(compfile)
                fullfile = os.path.join(layersubdir, compfile)
                datasubdir = os.path.join(layersubdir, compbase)
                compimage = os.path.join(compbase, "%s.%s" % (compbase, iType))
                if os.path.exists(datasubdir):
                    shutil.rmtree(datasubdir)
                os.makedirs(datasubdir)
                if (zipfileBroken == False):
                    if (cType == "TGZ"):
                        cFile = tarfile.open(fullfile)
                    elif (cType == "ZIP"):
                        cFile = zipfile.ZipFile(fullfile)
                    cFile.extract(compimage, layersubdir)
                    cFile.close()
                else:
                    if (cType == "TGZ"):
                        cFile = tarfile.open(fullfile)
                        cFile.extract(compimage, layersubdir)
                    elif (cType == "ZIP"):
                        omfgcompimage = "\\".join([compbase, "%s.%s" % (compbase, iType)])
                        os.mkdir(os.path.dirname(os.path.join(datasubdir,compimage)))
                        cFile = zipfile.ZipFile(fullfile)
                        cFile.extract(omfgcompimage, datasubdir)
                        os.rename(os.path.join(datasubdir,omfgcompimage),os.path.join(layersubdir,compimage))
                    cFile.close()
            os.system("cd %s && gdalbuildvrt -resolution highest %s.vrt */*.%s && gdal_translate %s.vrt %s.%s" % (layersubdir, layerID, iType, layerID, layerID, iType))

    def warpelevation(self):
        """Warp elevation file to match landcover file."""
        # NB: not multi-big-file-friendly
        elevationimage = ""
        landcoverimage = ""
        layerIDs = [ name for name in os.listdir(self.mapsdir) if os.path.isdir(os.path.join(self.mapsdir, name)) ]
        for layerID in layerIDs:
            (pType, iType, mType, cType) = decodeLayerID(layerID)
            dataname = os.path.join(self.mapsdir, layerID, "%s.%s" % (layerID, iType))
            if (pType == "elevation"):
                elevationimage = dataname
            elif (pType == "landcover"):
                landcoverimage = dataname
            else:
                raise AttributeError, "Product type %s not yet supported!" % pType
        if (elevationimage == ""):
            raise AttributeError, "Elevation image not found!"
        if (landcoverimage == ""):
            raise AttributeError, "Landcover image not found!"

        elevationimageorig = "%s-orig" % elevationimage
        os.rename(elevationimage, elevationimageorig)
        warpFile(elevationimageorig, elevationimage, landcoverimage)

    def getfiles(self):
        """Get files from USGS."""
        # transmit el values for both, don't ask why right now
        productIDs = (self.checkavail(self.mapxmin, self.mapxmax, self.mapymin, self.mapymax, landcoverIDs),
                      self.checkavail(self.mapxmin, self.mapxmax, self.mapymin, self.mapymax, elevationIDs))
        layerIDs = self.checkdownloadoptions(productIDs)
        downloadURLs = self.requestvalidation(layerIDs)
        for layerID in downloadURLs.keys():
            for downloadURL in downloadURLs[layerID]:
                self.downloadfile(layerID, downloadURL)
        self.extractfiles()
        self.warpelevation()
        
def checkRegion():
    epsilon = 0.000001 # comparing floating point with equals is wrong

    if True:
        try:
            BlockIsland = Region(name='BlockIsland', tilesize=255, ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332)
        except AttributeError:
            print "Mod 16 check passed"
        else:
            print "Mod 16 check failed"
            exit -1

    BlockIsland = Region(name='BlockIsland', ymax=41.2378, ymin=41.1415, xmin=-71.6202, xmax=-71.5332)
    try:
        assert (BlockIsland.mapxmax - -71.496356) < epsilon, "mapxmax does not check"
        assert (BlockIsland.mapxmin - -71.664006) < epsilon, "mapxmin does not check"
        assert (BlockIsland.mapymax - 41.264504) < epsilon, "mapymax does not check"
        assert (BlockIsland.mapymin - 41.120324) < epsilon, "mapymin does not check"
    except AssertionError:
        pass
    else:
        print "Region creation passed"

    yamlfile = file(os.path.join('Regions', 'BlockIsland', 'Region.yaml'))
    myyaml = yaml.load(yamlfile)
    yamlfile.close()
    try:
        assert myyaml['tilesize'] == BlockIsland.tilesize, 'YAML tilesize does not match'
        assert myyaml['scale'] == BlockIsland.scale, 'YAML scale does not match'
        assert myyaml['maxdepth'] == BlockIsland.maxdepth, 'YAML maxdepth does not match'
        assert (myyaml['mapxmax'] - BlockIsland.mapxmax) < epsilon, "YAML mapxmax does not match"
        assert (myyaml['mapxmin'] - BlockIsland.mapxmin) < epsilon, "YAML mapxmin does not match"
        assert (myyaml['mapymax'] - BlockIsland.mapymax) < epsilon, "YAML mapymax does not match"
        assert (myyaml['mapymin'] - BlockIsland.mapymin) < epsilon, "YAML mapymin does not match"
        assert myyaml['txmax'] == BlockIsland.txmax, 'YAML txmax does not match'
        assert myyaml['txmin'] == BlockIsland.txmin, 'YAML txmin does not match'
        assert myyaml['tymax'] == BlockIsland.tymax, 'YAML tymax does not match'
        assert myyaml['tymin'] == BlockIsland.tymin, 'YAML tymin does not match'
    except AssertionError:
        pass
    else:
        print "YAML check passed"

    BlockIsland.getfiles()
    
if __name__ == '__main__':
    checkRegion();
