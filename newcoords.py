# newcoords module

from osgeo import gdal, osr
import numpy

def getTransforms(ds):
    "Given a dataset, return the transform and geotransform."
    Projection = ds.GetProjectionRef()
    Proj = osr.SpatialReference(Projection)
    LatLong = Proj.CloneGeogCS()
    Trans = osr.CoordinateTransformation(Proj, LatLong)
    ArcTrans = osr.CoordinateTransformation(LatLong, Proj)
    GeoTrans = ds.GetGeoTransform()

    return Trans, ArcTrans, GeoTrans

def getCoordsArray(ds, xmin, ymin, xsize, ysize, func, scale=1):
    "Builds array with coordinates based on supplied function."
    cols = numpy.linspace(ymin*scale, (ymin+ysize)*scale, ysize, False)
    rows = numpy.linspace(xmin*scale, (xmin+xsize)*scale, xsize, False)
    retval = numpy.array([func(ds, row, col) for row in rows for col in cols])
    return retval

# in the definitions below:
# LL is lat-long in the real world
# Map is in the coordinate system of the dataset
# Raster is the position of the point in the dataset

def fromRastertoMap(ds, x, y):
    dfGeoX = ds.transforms[2][0] + ds.transforms[2][1] * x + ds.transforms[2][2] * y
    dfGeoY = ds.transforms[2][3] + ds.transforms[2][4] * x + ds.transforms[2][5] * y
    return dfGeoX, dfGeoY

def fromMaptoLL(ds, dfGeoX, dfGeoY):
    pnt = ds.transforms[0].TransformPoint(dfGeoX, dfGeoY, 0)
    return pnt[1], pnt[0]

def fromRastertoLL(ds, x, y):
    dfGeoX, dfGeoY = fromRastertoMap(ds, x, y)
    pnt1, pnt0 = fromMaptoLL(ds, dfGeoX, dfGeoY)
    return pnt1, pnt0

def getLatLong(ds, x, y):
    return fromRastertoLL(ds, x, y)

def fromLLtoMap(ds, lat, lon):
    pnt = ds.transforms[1].TransformPoint(lon, lat, 0)
    return pnt[0], pnt[1]

def fromMaptoRaster(ds, pnt0, pnt1):
    x = (pnt0 - ds.transforms[2][0])/ds.transforms[2][1]
    y = (pnt1 - ds.transforms[2][3])/ds.transforms[2][5]
    return round(x), round(y)

def fromLLtoRaster(ds, lat, lon):
    pnt0, pnt1 = fromLLtoMap(ds, lat, lon)
    x, y = fromMaptoRaster(ds, pnt0, pnt1)
    return x, y

def getCoords(ds, lat, lon):
    return fromLLtoRaster(ds, lat, lon)
