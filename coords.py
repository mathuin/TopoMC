# coords module

from osgeo import gdal, osr
import numpy

def getLatLongArray(ds, offset, size, mult=1):
    "Given transformations, dimensions, and multiplier, generate the interpolated array."
    rows = numpy.linspace(offset[1]/mult, (offset[1]+size[1])/mult, size[1], False)
    cols = numpy.linspace(offset[0]/mult, (offset[0]+size[0])/mult, size[0], False)
    retval = numpy.array([getLatLong(ds, row, col) for row in rows for col in cols])

    return retval

def getLatLong(ds, x, y):
    "Given dataset and coordinates, return latitude and longitude.  Based on GDALInfoReportCorner() from gdalinfo.py"
    #(Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    dfGeoX = ds.transforms[2][0] + ds.transforms[2][1] * x + ds.transforms[2][2] * y
    dfGeoY = ds.transforms[2][3] + ds.transforms[2][4] * x + ds.transforms[2][5] * y
    pnt = ds.transforms[0].TransformPoint(dfGeoX, dfGeoY, 0)
    return pnt[1], pnt[0]

def getTransforms(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Trans = osr.CoordinateTransformation(Proj, LatLong)
    ArcTrans = osr.CoordinateTransformation(LatLong, Proj)
    GeoTrans = ds.GetGeoTransform()

    return Trans, ArcTrans, GeoTrans

def getCoords(ds, lat, lon):
    "The backwards version of getLatLong, from geo_trans.c."
    #(Trans, ArcTrans, GeoTrans) = getTransforms(ds)
    pnt = ds.transforms[1].TransformPoint(lon, lat, 0)
    x = (pnt[0] - ds.transforms[2][0])/ds.transforms[2][1]
    y = (pnt[1] - ds.transforms[2][3])/ds.transforms[2][5]
    return round(x), round(y)

