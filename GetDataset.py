#!/usr/bin/env python

from __future__ import division
import suds
import re
import urllib2
import sys
import os
import shutil
import argparse
from lxml import etree
from time import sleep
from dataset import landcoverIDs, elevationIDs
#import logging
#logging.basicConfig(level=logging.INFO)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)

def cleanDatasetDir(args):
    "Clean up the dataset directory."
    datasetName = args.region
    datasetDir = os.path.join("Datasets",datasetName)
    if os.path.exists(datasetDir):
        shutil.rmtree(datasetDir)
    os.makedirs(datasetDir)

    return datasetDir

def checkInventory(args):
    "Check the USGS inventory for the desired landcover and elevation data."
    useNew = True
    if (useNew):
        # Deb from the USGS recommended I do this:
        #  - convert desired extents from WGS84 to Albers
        #  - take the max in each direction to form a rectangle
        #    (new landcover extents)
        #  - convert these corners to WGS84 from Albers
        #    (new elevation extents)
        wgs84 = 4326
        albers = 102039

        wsdlConv = "http://extract.cr.usgs.gov/XMLWebServices/Coordinate_Conversion_Service.asmx?WSDL"
        clientConv = suds.client.Client(wsdlConv)
        # This web service returns suds.sax.text.Text not XML sigh
        Convre = "<X Coordinate>(.*?)</X Coordinate > <Y Coordinate>(.*?)</Y Coordinate >"

        # step one: convert from WGS84 to Albers
        # UL: xmin, ymin
        ULdict = {'X_Value': args.xmin, 'Y_Value': args.ymin, 'Current_Coordinate_System': wgs84, 'Target_Coordinate_System': albers}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        # UR: xmax, ymin
        URdict = {'X_Value': args.xmax, 'Y_Value': args.ymin, 'Current_Coordinate_System': wgs84, 'Target_Coordinate_System': albers}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        # LL: xmin, ymax
        LLdict = {'X_Value': args.xmin, 'Y_Value': args.ymax, 'Current_Coordinate_System': wgs84, 'Target_Coordinate_System': albers}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        # LR: xmax, ymax
        LRdict = {'X_Value': args.xmax, 'Y_Value': args.ymax, 'Current_Coordinate_System': wgs84, 'Target_Coordinate_System': albers}
        (LRx, LRy) = re.findall(Convre, clientConv.service.getCoordinates(**LRdict))[0]

        # step two: select maximum values for landcover extents
        lcxmax = max(ULx, URx, LLx, LRx)
        lcxmin = min(ULx, URx, LLx, LRx)
        lcymax = max(ULy, URy, LLy, LRy)
        lcymin = min(ULy, URy, LLy, LRy)

        # step three: convert to WGS84 from Albers
        # UL: xmin, ymin
        ULdict = {'X_Value': lcxmin, 'Y_Value': lcymin, 'Current_Coordinate_System': albers, 'Target_Coordinate_System': wgs84}
        (ULx, ULy) = re.findall(Convre, clientConv.service.getCoordinates(**ULdict))[0]
        # UR: xmax, ymin
        URdict = {'X_Value': lcxmax, 'Y_Value': lcymin, 'Current_Coordinate_System': albers, 'Target_Coordinate_System': wgs84}
        (URx, URy) = re.findall(Convre, clientConv.service.getCoordinates(**URdict))[0]
        # LL: xmin, ymax
        LLdict = {'X_Value': lcxmin, 'Y_Value': lcymax, 'Current_Coordinate_System': albers, 'Target_Coordinate_System': wgs84}
        (LLx, LLy) = re.findall(Convre, clientConv.service.getCoordinates(**LLdict))[0]
        # LR: xmax, ymax
        LRdict = {'X_Value': lcxmax, 'Y_Value': lcymax, 'Current_Coordinate_System': albers, 'Target_Coordinate_System': wgs84}
        (LRx, LRy) = re.findall(Convre, clientConv.service.getCoordinates(**LRdict))[0]

        # step two: select maximum values for landcover extents
        xfloat = [float(x) for x in [ULx, URx, LLx, LRx]]
        yfloat = [float(y) for y in [ULy, URy, LLy, LRy]]
        elevxmax = max(xfloat)
        elevxmin = min(xfloat)
        elevymax = max(yfloat)
        elevymin = min(yfloat)

        # check availability
        #lcProduct = checkAvail(lcxmin, lcxmax, lcymin, lcymax, landcoverIDs, albers)
        lcProduct = checkAvail(args.xmin, args.xmax, args.ymin, args.ymax, landcoverIDs)
        elevProduct = checkAvail(elevxmin, elevxmax, elevymin, elevymax, elevationIDs)
    else:
    
        # elevation extents are based on landcover extents
        # each side of elevation is equal to sum of landcover edges

        # first calculate center of region
        centerx = (args.xmin+args.xmax)/2
        centery = (args.ymin+args.ymax)/2
        halfelevside = ((args.xmax-args.xmin)+(args.ymax-args.ymin))/2

        # now calculate elevation extents
        elevxmin = centerx-halfelevside
        elevxmax = centerx+halfelevside
        elevymin = centery-halfelevside
        elevymax = centery+halfelevside

        # check availability
        lcProduct = checkAvail(args.xmin, args.xmax, args.ymin, args.ymax, landcoverIDs)
        # elevProduct = checkAvail(elevxmin, elevxmax, elevymin, elevymax, elevationIDs)
        elevProduct = checkAvail(args.xmin, args.xmax, args.ymin, args.ymax, elevationIDs)

    # return product ID and edges
    return (lcProduct, elevProduct)

def checkAvail(xmin, xmax, ymin, ymax, productlist, epsg=4326):
    "Check inventory service for coverage."
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
        print "no attributes found"
        return -1
    
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
    return None

def checkDownloadOptions(productIDs):
    "Check download options for product IDs."
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
        # I want GeoTIFF, HTML and ZIP here
        # should use list in order of preference like landcoverIDs etc
        if u'GeoTIFF' in outputformats:
            layerID += outputformats['GeoTIFF']
        else:
            print "oh no GeoTIFF not available"
            return -1
        if u'HTML' in metadataformats:
            layerID += metadataformats['HTML']
        else:
            print "oh no HTML not available"
            return -1
        if u'ZIP' in compressionformats:
            layerID += compressionformats['ZIP']
        else:
            print "oh no ZIP not available"
            return -1
        layerIDs.append([layerID, xmin, xmax, ymin, ymax])

    return layerIDs

def requestValidation(layerIDs):
    "Generates download URLs from layer IDs." 
    retval = {}

    # request validation
    wsdlRequest = "http://extract.cr.usgs.gov/requestValidationService/wsdl/RequestValidationService.wsdl"
    clientRequest = suds.client.Client(wsdlRequest)

    # we now iterate through layerIDs
    for layerID in layerIDs:
        (tag, xmin, xmax, ymin, ymax) = layerID
        xmlString = "<REQUEST_SERVICE_INPUT><AOI_GEOMETRY><EXTENT><TOP>%f</TOP><BOTTOM>%f</BOTTOM><LEFT>%f</LEFT><RIGHT>%f</RIGHT></EXTENT><SPATIALREFERENCE_WKID/></AOI_GEOMETRY><LAYER_INFORMATION><LAYER_IDS>%s</LAYER_IDS></LAYER_INFORMATION><CHUNK_SIZE>%d</CHUNK_SIZE><JSON></JSON></REQUEST_SERVICE_INPUT>" % (ymax, ymin, xmin, xmax, tag, 250)

        response = clientRequest.service.processAOI(xmlString)

        print "Requested URLs for layer ID %s..." % tag

        # I am a bad man.
        downloadURLre = "<DOWNLOAD_URL>(.*?)</DOWNLOAD_URL>"
        downloadURLs = [m.group(1) for m in re.finditer(downloadURLre, response)]

        retval[tag] = downloadURLs

    return retval

# stupid redirect handling craziness
class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp,
                                                                 code, msg,
                                                                 headers)
        result.status = code
        result.headers = headers
        return result

def downloadFile(layerID, downloadURL, datasetDir):
    "Actually download the file at the URL."
    # FIXME: extract try/expect around urlopen
    # FIXME: consider breaking apart further
    layerDir = os.path.join(datasetDir,layerID)
    if not os.path.exists(layerDir):
        os.makedirs(layerDir)

    print "  Requesting download."
    # initiateDownload and get the response code
    # put _this_ in its own function!
    try:
        page = urllib2.urlopen(downloadURL)
    except IOError, e:
        if hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
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
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
    else:
        print "  downloading %s now!" % filename
        downloadFile = open(os.path.join(layerDir,filename), 'wb')
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
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
    else:
        result = page4.read()
        page4.close()
        # remove carriage returns
        result = result.replace("&#xd;\n"," ")
        # parse out status code and status text
        startPos = result.find("<ns:return>") + 11
        endPos = result.find("</ns:return>")
        status = result[startPos:endPos]

def main(argv):
    "The main routine."

    # parse options and get results
    parser = argparse.ArgumentParser(description='Retrieve datasets from USGS Seamless Web services.')
    parser.add_argument('--region', required=True, type=str, help='a region to be generated')
    parser.add_argument('--xmax', required=True, type=float, help='easternmost longitude (west is negative)')
    parser.add_argument('--xmin', required=True, type=float, help='westernmost longitude (west is negative)')
    parser.add_argument('--ymax', required=True, type=float, help='northernmost latitude (south is negative)')
    parser.add_argument('--ymin', required=True, type=float, help='southernmost longitude (south is negative)')
    args = parser.parse_args()

    # test case
    # args.region = "BlockIsland-New"
    # args.xmin = -71.623
    # args.xmax = -71.529
    # args.ymin = 41.138
    # args.ymax = 41.24

    # tell the user what's going on
    print "Retrieving new dataset %s..." % args.region

    # clean dataset
    datasetDir = cleanDatasetDir(args)

    print "Checking inventory service for coverage."

    productIDs = checkInventory(args)
    print "Inventory service has the following product IDs: %s" % ','.join([elem[0] for elem in productIDs])

    layerIDs = checkDownloadOptions(productIDs)
    print "Configured the following layer IDs: %s" % ','.join([elem[0] for elem in layerIDs])

    # this is now a dict
    downloadURLs = requestValidation(layerIDs)
    print "Received download URLs, downloading now!"
    for layerID in downloadURLs.keys():
        for downloadURL in downloadURLs[layerID]:
            downloadFile(layerID, downloadURL, datasetDir)
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))
