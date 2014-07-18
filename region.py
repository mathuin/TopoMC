#!/usr/bin/env python

from __future__ import division
from math import ceil, floor
import os
import os.path
import yaml
import logging
logging.basicConfig(level=logging.INFO)
from utils import cleanmkdir
from terrain import Terrain
from pymclevel import mclevel

from osgeo import gdal, osr, ogr
from osgeo.gdalconst import GDT_Int16, GA_ReadOnly
from bathy import Bathy
from crust import Crust
import numpy as np

from idt import IDT
from elev import Elev


class Region:
    """Primary class for regions."""

    # coordinate systems
    wgs84 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
    albers = "+proj=aea +datum=NAD83 +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +x_0=0 +y_0=0 +units=m"

    # raster layer order
    rasters = {'landcover': 1, 'elevation': 2, 'bathy': 3, 'crust': 4}

    # sadness
    gdalwarp_broken_for_landcover = True

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

    # download directory
    downloadtop = os.path.abspath('downloads')
    regiontop = os.path.abspath('regions')

    # properties
    @property
    def regiondir(self):
        return os.path.join(Region.regiontop, self.name)

    @property
    def regionfile(self):
        return os.path.join(self.regiondir, 'Region.yaml')

    @property
    def mapsdir(self):
        return os.path.join(self.regiondir, 'Datasets')

    @property
    def mapfile(self):
        return os.path.join(self.regiondir, 'Map.tif')

    def __init__(self, name, xmax, xmin, ymax, ymin, tilesize=None, scale=None, vscale=None, trim=None, sealevel=None, maxdepth=None, lcfiles=None, elfiles=None, doOre=True, doSchematics=False):
        """Create a region based on lat-longs and other parameters."""
        # NB: smart people check names
        self.name = name

        # tile must be an even multiple of chunk width
        # chunkWidth not defined in pymclevel but is hardcoded everywhere
        if tilesize is None:
            tilesize = Region.tilesize
        else:
            if tilesize % 16 != 0:
                raise AttributeError('bad tilesize %s' % tilesize)
        self.tilesize = tilesize

        # scale can be any positive integer
        if scale is None:
            scale = Region.scale
        else:
            if scale > 0:
                self.scale = int(scale)
            else:
                raise AttributeError('bad scale %s' % scale)

        # sealevel and maxdepth are not checked until after files are retrieved
        if sealevel is None:
            sealevel = Region.sealevel
        else:
            self.sealevel = sealevel

        if maxdepth is None:
            maxdepth = Region.maxdepth
        else:
            self.maxdepth = maxdepth

        # trim and vscale are not checked until after files are retrieved
        if trim is None:
            trim = Region.trim
        else:
            self.trim = trim

        if vscale is None:
            vscale = Region.vscale
        else:
            self.vscale = vscale

        # lcfiles and elfiles are currently being passed as arguments
        if lcfiles is None:
            raise AttributeError("lcfiles required")
        else:
            lclist = lcfiles.split(',')
            for lcelem in lclist:
                if not os.path.isfile(lcelem):
                    raise AttributeError("%s is not a file", lcelem)
            self.lcfiles = lclist

        if elfiles is None:
            raise AttributeError("elfiles required")
        else:
            ellist = elfiles.split(',')
            for elelem in ellist:
                if not os.path.isfile(elelem):
                    raise AttributeError("%s is not a file", elelem)
            self.elfiles = ellist

        # enable or disable ore and schematics
        self.doOre = doOre
        self.doSchematics = doSchematics

        # crazy directory fun
        cleanmkdir(self.regiondir)
        cleanmkdir(self.mapsdir)

        # these are the latlong values
        self.llextents = {'xmax': max(xmax, xmin), 'xmin': min(xmax, xmin), 'ymax': max(ymax, ymin), 'ymin': min(ymax, ymin)}

        # Convert from WGS84 to Albers.
        [mxmax, mxmin, mymax, mymin] = Region.get_corners(Region.wgs84, Region.albers, xmax, xmin, ymax, ymin)

        # calculate tile edges
        realsize = self.scale * self.tilesize
        self.tiles = {'xmax': int(ceil(mxmax / realsize)), 'xmin': int(floor(mxmin / realsize)), 'ymax': int(ceil(mymax / realsize)), 'ymin': int(floor(mymin / realsize))}

        self.albersextents = {'landcover': dict(), 'elevation': dict()}
        self.wgs84extents = {'landcover': dict(), 'elevation': dict()}

        # Landcover needs a maxdepth-sized border for bathy calculations.
        self.albersextents['elevation'] = {'xmax': self.tiles['xmax'] * realsize,
                                           'xmin': self.tiles['xmin'] * realsize,
                                           'ymax': self.tiles['ymax'] * realsize,
                                           'ymin': self.tiles['ymin'] * realsize}
        borderwidth = self.maxdepth * self.scale
        self.albersextents['landcover'] = {'xmax': self.albersextents['elevation']['xmax'] + borderwidth,
                                           'xmin': self.albersextents['elevation']['xmin'] - borderwidth,
                                           'ymax': self.albersextents['elevation']['ymax'] + borderwidth,
                                           'ymin': self.albersextents['elevation']['ymin'] - borderwidth}

        # Now convert back from Albers to WGS84.
        for maptype in ['landcover', 'elevation']:
            [wxmax, wxmin, wymax, wymin] = Region.get_corners(Region.albers, Region.wgs84, self.albersextents[maptype]['xmax'], self.albersextents[maptype]['xmin'], self.albersextents[maptype]['ymax'], self.albersextents[maptype]['ymin'])
            self.wgs84extents[maptype] = {'xmax': wxmax, 'xmin': wxmin, 'ymax': wymax, 'ymin': wymin}

        # write the values to the file
        stream = file(os.path.join(self.regionfile), 'w')
        yaml.dump(self, stream)
        stream.close()

    @staticmethod
    def get_corners(fromCS, toCS, xmax, xmin, ymax, ymin):
        """Transform the given extents from a source SR to a destination SR."""

        fromSR = osr.SpatialReference()
        fromSR.ImportFromProj4(fromCS)
        toSR = osr.SpatialReference()
        toSR.ImportFromProj4(toCS)

        corners = [(x, y) for y in [ymin, ymax] for x in [xmin, xmax]]

        xfloat = []
        yfloat = []
        for corner in corners:
            point = ogr.CreateGeometryFromWkt('POINT(%s %s)' % (corner[0], corner[1]))
            point.AssignSpatialReference(fromSR)
            point.TransformTo(toSR)
            xfloat.append(point.GetX())
            yfloat.append(point.GetY())

        return [max(xfloat), min(xfloat), max(yfloat), min(yfloat)]

    def unzipfiles(self, layertype, zipfile):
        """Extract relevant files from ZIP file."""
        templates = {'elevation': ['%s', 'img%s_13'],
                     'landcover': ['%s']}
        suffixes = {'elevation': ['img'],
                    'landcover': ['tif', 'tfw']}
        layerdir = os.path.join(Region.downloadtop, layertype)
        if not os.path.exists(layerdir):
            os.makedirs(layerdir)
        extracthead = os.path.basename(zipfile).split('.')[0]
        extractfiles = []
        for template in templates[layertype]:
            basefile = template % extracthead
            for suffix in suffixes[layertype]:
                checkfile = '%s.%s' % (basefile, suffix)
                retval = os.system('unzip -l "%s" "%s">/dev/null' % (zipfile, checkfile))
                if retval == 0:
                    # file is present!
                    extractfiles.append(checkfile)
        if extractfiles == []:
            print "OMG need better templates!"

        for extractfile in extractfiles:
            if os.path.exists(os.path.join(layerdir, extractfile)):
                print "Using existing file %s for %s layer" % (extractfile, layertype)
            else:
                os.system('unzip "%s" "%s" -d "%s"' % (zipfile, extractfile, layerdir))
        return os.path.join(layerdir, extractfiles[0])

    def maketiffs(self):
        """Construct warped GeoTIFFs from source files."""

        # JMT: at this point only one file per dataset works!
        # I am now thinking of redefining lcfile
        # "x,y,z" -> [x,y,z] "x" -> [x]
        layerfiles = {'landcover': self.lcfiles,
                      'elevation': self.elfiles}

        for layertype in layerfiles:
            zipfiles = layerfiles[layertype]
            extractlist = []
            for zipfile in zipfiles:
                extractfile = self.unzipfiles(layertype, zipfile)
                extractlist.append(extractfile)
            # Build VRTs
            vrtfile = os.path.join(self.mapsdir, '%s.vrt' % layertype)
            buildvrtcmd = 'gdalbuildvrt "%s" %s' % (vrtfile, ' '.join(['"%s"' % os.path.abspath(extractfile) for extractfile in extractlist]))
            os.system('%s' % buildvrtcmd)
            # Generate warped GeoTIFFs
            tiffile = os.path.join(self.mapsdir, '%s.tif' % layertype)
            warpcmd = 'gdalwarp -q -multi -t_srs "%s" "%s" "%s"' % (Region.albers, vrtfile, tiffile)
            os.system('%s' % warpcmd)

    def build_map(self, wantCL=True, do_pickle=False):
        """Use downloaded files and other parameters to build multi-raster map."""

        # set pickle variable
        if do_pickle:
            pickle_name = self.name
        else:
            pickle_name = None

        # warp elevation data into new format
        # NB: can't do this to landcover until mode algorithm is supported
        eltif = os.path.join(self.mapsdir, 'elevation.tif')
        elfile = os.path.join(self.mapsdir, 'elevation-new.tif')
        elextents = self.albersextents['elevation']
        warpcmd = 'gdalwarp -q -multi -tr %d %d -te %d %d %d %d -r cubic "%s" "%s" -srcnodata "-340282346638529993179660072199368212480.000" -dstnodata 0' % (self.scale, self.scale, elextents['xmin'], elextents['ymin'], elextents['xmax'], elextents['ymax'], eltif, elfile)

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
        if elmin < 0:
            minsealevel += int(-1.0*elmin/self.scale)
        maxsealevel = Region.tileheight - Region.headroom
        oldsealevel = self.sealevel
        if oldsealevel > maxsealevel or oldsealevel < minsealevel:
            print "warning: sealevel value %d outside %d-%d range" % (oldsealevel, minsealevel, maxsealevel)
        self.sealevel = int(min(max(oldsealevel, minsealevel), maxsealevel))

        # maxdepth depends upon sealevel
        minmaxdepth = 1
        maxmaxdepth = self.sealevel - 1
        oldmaxdepth = self.maxdepth
        if oldmaxdepth > maxmaxdepth or oldmaxdepth < minmaxdepth:
            print "warning: maxdepth value %d outside %d-%d range" % (oldmaxdepth, minmaxdepth, maxmaxdepth)
        self.maxdepth = int(min(max(oldmaxdepth, minmaxdepth), maxmaxdepth))

        # trim depends upon elmin (if elmin < 0, trim == 0)
        mintrim = Region.trim
        maxtrim = max(elmin, mintrim)
        oldtrim = self.trim
        if oldtrim > maxtrim or oldtrim < mintrim:
            print "warning: trim value %d outside %d-%d range" % (oldtrim, mintrim, maxtrim)
        self.trim = int(min(max(oldtrim, mintrim), maxtrim))

        # vscale depends on sealevel, trim and elmax
        # NB: no maximum vscale, the sky's the limit (hah!)
        eltrimmed = elmax - self.trim
        elroom = Region.tileheight - Region.headroom - self.sealevel
        minvscale = ceil(eltrimmed / elroom)
        oldvscale = self.vscale
        if oldvscale < minvscale:
            print "warning: vscale value %d smaller than minimum value %d" % (oldvscale, minvscale)
        self.vscale = int(max(oldvscale, minvscale))

        # GeoTIFF
        # four bands: landcover, elevation, bathy, crust
        # data type is GDT_Int16 (elevation can be negative)
        driver = gdal.GetDriverByName("GTiff")
        mapds = driver.Create(self.mapfile, elxsize, elysize, len(Region.rasters), GDT_Int16)
        # overall map transform should match elevation map transform
        mapds.SetGeoTransform(elgeotrans)
        srs = osr.SpatialReference()
        srs.ImportFromProj4(Region.albers)
        mapds.SetProjection(srs.ExportToWkt())

        # modify elarray and save it as raster band 2
        elevObj = Elev(elarray, wantCL=wantCL)
        actualel = elevObj(self.trim, self.vscale, self.sealevel, pickle_name=pickle_name)
        mapds.GetRasterBand(Region.rasters['elevation']).WriteArray(actualel)
        elarray = None
        actualel = None

        # generate crust and save it as raster band 4
        newcrust = Crust(mapds.RasterXSize, mapds.RasterYSize, wantCL=wantCL)
        crustarray = newcrust(pickle_name=pickle_name)
        mapds.GetRasterBand(Region.rasters['crust']).WriteArray(crustarray)
        crustarray = None
        newcrust = None

        # read landcover array
        lctif = os.path.join(self.mapsdir, 'landcover.tif')
        lcfile = os.path.join(self.mapsdir, 'landcover-new.tif')
        # here are the things that need to happen
        lcextents = self.albersextents['landcover']

        # if True, use new code, if False, use gdalwarp
        if Region.gdalwarp_broken_for_landcover:
            # 1. the new file must be read into an array and flattened
            tifds = gdal.Open(lctif, GA_ReadOnly)
            tifgeotrans = tifds.GetGeoTransform()
            tifband = tifds.GetRasterBand(1)
            xminarr = int((lcextents['xmin']-tifgeotrans[0])/tifgeotrans[1])
            xmaxarr = int((lcextents['xmax']-tifgeotrans[0])/tifgeotrans[1])
            yminarr = int((lcextents['ymax']-tifgeotrans[3])/tifgeotrans[5])
            ymaxarr = int((lcextents['ymin']-tifgeotrans[3])/tifgeotrans[5])
            values = tifband.ReadAsArray(xminarr, yminarr, xmaxarr-xminarr, ymaxarr-yminarr)
            # nodata is treated as water, which is 11
            tifnodata = tifband.GetNoDataValue()
            if tifnodata is None:
                tifnodata = 0
            values[values == tifnodata] = 11
            values = values.flatten()
            tifband = None
            # 2. a new array of original scale coordinates must be created
            tifxrange = [tifgeotrans[0] + tifgeotrans[1] * x for x in xrange(xminarr, xmaxarr)]
            tifyrange = [tifgeotrans[3] + tifgeotrans[5] * y for y in xrange(yminarr, ymaxarr)]
            tifds = None
            coords = np.array([(x, y) for y in tifyrange for x in tifxrange])
            # 3. a new array of goal scale coordinates must be made
            # landcover extents are used for the bathy depth array
            # yes, it's confusing.  sorry.
            depthxlen = int((lcextents['xmax']-lcextents['xmin'])/self.scale)
            depthylen = int((lcextents['ymax']-lcextents['ymin'])/self.scale)
            depthxrange = [lcextents['xmin'] + self.scale * x for x in xrange(depthxlen)]
            depthyrange = [lcextents['ymax'] - self.scale * y for y in xrange(depthylen)]
            depthbase = np.array([(x, y) for y in depthyrange for x in depthxrange], dtype=np.float32)
            # 4. an inverse distance tree must be built from that
            lcIDT = IDT(coords, values.ravel().astype(np.int32), wantCL=wantCL)
            # 5. the desired output comes from that inverse distance tree
            depthshape = (depthylen, depthxlen)
            deptharray = lcIDT(depthbase, depthshape, pickle_name=pickle_name)
            lcIDT = None
        else:
            warpcmd = 'gdalwarp -q -multi -tr %d %d -te %d %d %d %d -r near "%s" "%s"' % (self.scale, self.scale, lcextents['xmin'], lcextents['ymin'], lcextents['xmax'], lcextents['ymax'], lctif, lcfile)

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
        geotrans = [lcextents['xmin'], self.scale, 0, lcextents['ymax'], 0, -1 * self.scale]
        projection = srs.ExportToWkt()
        bathyObj = Bathy(deptharray, geotrans, projection, wantCL=wantCL)
        bathyarray = bathyObj(self.maxdepth, pickle_name=pickle_name)
        mapds.GetRasterBand(Region.rasters['bathy']).WriteArray(bathyarray)
        # perform terrain translation
        # NB: figure out why this doesn't work up above
        #lcpid = self.lclayer[:3]
        # JMT: hardcoded for now
        lcpid = 'L1L'
        if lcpid in Terrain.translate:
            trans = Terrain.translate[lcpid]
            for key in trans:
                lcarray[lcarray == key] = trans[key]
            for value in np.unique(lcarray).flat:
                if value not in Terrain.terdict:
                    print "bad value: ", value
        mapds.GetRasterBand(Region.rasters['landcover']).WriteArray(lcarray)

        # close the dataset
        mapds = None
