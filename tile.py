# tile module
import Image
from time import time
from dataset import *
from coords import *
from invdisttree import *
from bathy import getBathymetry
from crust import getCrust
from dataset import getDatasetDims, getDatasetElevs
from multiprocessing import Pool
from itertools import product
from mcarray import maxelev
from terrain import processTerrain
import logging
logging.basicConfig(level=logging.WARNING)
tilelogger = logging.getLogger('tile')

def getIDT(ds, offset, size, vScale=1, nodata=None, trim=0):
    "Convert a portion of a given dataset (identified by corners) to an inverse distance tree."
    # retrieve data from dataset
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])

    # set nodata if it exists
    if (nodata != None):
        fromnodata = Band.GetNoDataValue()
        Data[Data == fromnodata] = nodata
    Band = None

    # build initial arrays
    LatLong = getLatLongArray(ds, (offset), (size), 1)
    Value = Data.flatten()

    # trim elevation
    if (trim > 0):
        Value = Value - trim

    # scale elevation vertically
    Value = Value / vScale

    # build tree
    IDT = Invdisttree(LatLong, Value)

    return IDT

def getOffsetSize(ds, corners, mult=1):
    "Convert corners to offset and size."
    (ul, lr) = corners
    ox, oy = getCoords(ds, ul[0], ul[1])
    offset_x = max(ox, 0)
    offset_y = max(oy, 0)
    fcx, fcy = getCoords(ds, lr[0], lr[1])
    farcorner_x = min(fcx, ds.RasterXSize)
    farcorner_y = min(fcy, ds.RasterYSize)
    offset = (int(offset_x*mult), int(offset_y*mult))
    size = (int(farcorner_x*mult-offset_x*mult), int(farcorner_y*mult-offset_y*mult))
    tilelogger.debug("offset is %d, %d, size is %d, %d" % (offset[0], offset[1], size[0], size[1]))
    return offset, size

def getImageArray(ds, idtCorners, baseArray, vScale=1, nodata=None, majority=False, trim=0):
    "Given the relevant information, builds the image array."
    Offset, Size = getOffsetSize(ds, idtCorners)
    IDT = getIDT(ds, Offset, Size, vScale, nodata, trim)
    ImageArray = IDT(baseArray, nnear=8, eps=0.1, majority=majority)

    return ImageArray

def getTileOffsetSize(rowIndex, colIndex, tileShape, maxRows, maxCols, idtPad=0):
    "run this with idtPad=0 to generate image."
    imageRows = tileShape[0]
    imageCols = tileShape[1]
    imageLeft = max(rowIndex*imageRows-idtPad, 0)
    imageRight = min(imageLeft+imageRows+2*idtPad, maxRows)
    imageUpper = max(colIndex*imageCols-idtPad, 0)
    imageLower = min(imageUpper+imageCols+2*idtPad, maxCols)
    imageOffset = (imageLeft, imageUpper)
    imageSize = (imageRight-imageLeft, imageLower-imageUpper)
    return imageOffset, imageSize

# adding processImage code to processTile
def processTile(args, tileRowIndex, tileColIndex):
    "Actually process a tile."
    tileShape = args.tile
    mult = args.mult
    curtime = time()
    (lcds, elevds) = getDataset(args.region)
    (rows, cols) = getDatasetDims(args.region)
    (elevmin, elevmax) = getDatasetElevs(args.region)
    maxRows = int(rows*mult)
    maxCols = int(cols*mult)
    baseOffset, baseSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols)
    idtOffset, idtSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols, idtPad=tileShape[0]+tileShape[1])
    tilelogger.info("Generating tile (%d, %d) with dimensions (%d, %d) and offset (%d, %d)..." % (tileRowIndex, tileColIndex, baseSize[0], baseSize[1], baseOffset[0], baseOffset[1]))

    baseShape = (baseSize[1], baseSize[0])
    baseArray = getLatLongArray(lcds, baseOffset, baseSize, mult)
    #idtShape = (idtSize[1], idtSize[0])
    #idtArray = getLatLongArray(lcds, idtOffset, idtSize, mult)

    # these points are scaled coordinates
    idtUL = getLatLong(lcds, int(idtOffset[0]/mult), int(idtOffset[1]/mult))
    idtLR = getLatLong(lcds, int((idtOffset[0]+idtSize[0])/mult), int((idtOffset[1]+idtSize[1])/mult))

    # nodata for landcover is equal to 11
    lcImageArray = getImageArray(lcds, (idtUL, idtLR), baseArray, nodata=11, majority=True)
    lcImageArray.resize(baseShape)

    # elevation array
    elevImageArray = getImageArray(elevds, (idtUL, idtLR), baseArray, args.vscale, trim=elevmin)
    elevImageArray.resize(baseShape)

    # TODO: go through the arrays for some special transmogrification
    # first idea: bathymetry
    depthOffset, depthSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols, idtPad=args.maxdepth)
    depthShape = (depthSize[1], depthSize[0])
    depthArray = getLatLongArray(lcds, depthOffset, depthSize, mult)
    depthUL = getLatLong(lcds, int(depthOffset[0]/mult), int(depthOffset[1]/mult))
    depthLR = getLatLong(lcds, int((depthOffset[0]+depthSize[0])/mult), int((depthOffset[1]+depthSize[1])/mult))
    bigImageArray = getImageArray(lcds, (depthUL, depthLR), depthArray, majority=True)
    bigImageArray.resize(depthShape)
    bathyImageArray = getBathymetry(args, lcImageArray, bigImageArray, baseOffset, depthOffset)

    # second idea: crust
    crustImageArray = getCrust(bathyImageArray, baseArray)
    crustImageArray.resize(baseShape)

    # now we do what we do in processImage
    localmax = 0
    spawnx = 10
    spawnz = 10

    for tilex, tilez in product(xrange(baseSize[0]), xrange(baseSize[1])):
        lcval = int(lcImageArray[tilez,tilex])
        elevval = int(elevImageArray[tilez,tilex])
        bathyval = int(bathyImageArray[tilez,tilex])
        crustval = int(crustImageArray[tilez,tilex])
        real_x = baseOffset[0] + tilex
        real_z = baseOffset[1] + tilez
        if (elevval < 0):
            print "OMG elevval %d is less than zero" % (elevval)
        if (elevval > maxelev):
            tilelogger.warning('Elevation %d exceeds maximum elevation (%d)' % (elevval, maxelev))
            elevval = maxelev
        if (elevval > localmax):
            localmax = elevval
            spawnx = real_x
            spawnz = real_z
        processTerrain([(lcval, real_x, real_z, elevval, bathyval, crustval)])
    tilelogger.info('... done with (%d, %d) in %f seconds!' % (tileRowIndex, tileColIndex, (time()-curtime)))
    return (spawnx, spawnz, localmax)

def processTilestar(args):
    return processTile(*args)

def processTiles(args, minTileRows, maxTileRows, minTileCols, maxTileCols, processes):
    "Process those tiles."
    # process data in 256x256 tiles
    if (processes == 1):
        peaks = [processTile(args, tileRowIndex, tileColIndex) for tileRowIndex in xrange(minTileRows, maxTileRows) for tileColIndex in xrange(minTileCols, maxTileCols)]
    else:
        pool = Pool(processes)
        tasks = [(args, tileRowIndex, tileColIndex) for tileRowIndex in xrange(minTileRows, maxTileRows) for tileColIndex in xrange(minTileCols, maxTileCols)]
        results = pool.imap_unordered(processTilestar, tasks)
        peaks = [x for x in results]
	pool = None
    return peaks

def checkTile(args, mult):
    "Checks to see if a tile dimension is too big for a region."
    oldtilex, oldtiley = args.tile
    rows, cols = getDatasetDims(args.region)
    maxRows = int(rows * mult)
    maxCols = int(cols * mult)
    tilex = min(oldtilex, maxRows)
    tiley = min(oldtiley, maxCols)
    if (tilex != oldtilex or tiley != oldtiley):
        tilelogger.warning("Tile size of %d, %d for region %s is too large -- changed to %d, %d" % (oldtilex, oldtiley, args.region, tilex, tiley))
    args.tile = (tilex, tiley)
    return (tilex, tiley)

def checkStartEnd(args, mult, tile):
    "Checks to see if start and end values are valid for a region."
    (rows, cols) = getDatasetDims(args.region)
    (minTileRows, minTileCols) = args.start
    (maxTileRows, maxTileCols) = args.end
    (tileRows, tileCols) = tile

    numRowTiles = int((rows*mult+tileRows-1)/tileRows)
    numColTiles = int((cols*mult+tileCols-1)/tileCols)
    # maxTileRows and maxTileCols default to 0 meaning do everything
    if (maxTileRows == 0 or maxTileRows > numRowTiles):
        if (maxTileRows > numRowTiles):
            tilelogger.warning("maxTileRows greater than numRowTiles, setting to %d" % numRowTiles)
        maxTileRows = numRowTiles
    if (minTileRows > maxTileRows):
        tilelogger.warning("minTileRows less than maxTileRows, setting to %d" % maxTileRows)
        minTileRows = maxTileRows
    if (maxTileCols == 0 or maxTileCols > numColTiles):
        if (maxTileCols > numColTiles):
            tilelogger.warning("maxTileCols greater than numColTiles, setting to %d" % numColTiles)
        maxTileCols = numColTiles
    if (minTileCols > maxTileCols):
        tilelogger.warning("minTileCols less than maxTileCols, setting to %d" % maxTileCols)
        minTileCols = maxTileCols
    return (minTileRows, minTileCols, maxTileRows, maxTileCols)

