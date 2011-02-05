# tile module
import Image
from time import time
from dataset import *
from coords import *
from invdisttree import *
from bathy import getBathymetry

def getIDT(ds, offset, size, vScale=1):
    "Convert a portion of a given dataset (identified by corners) to an inverse distance tree."
    # retrieve data from dataset
    Band = ds.GetRasterBand(1)
    Data = Band.ReadAsArray(offset[0], offset[1], size[0], size[1])
    Band = None

    # build initial arrays
    LatLong = getLatLongArray(ds, (offset), (size), 1)
    Value = Data.flatten()

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
    return offset, size

def getImageArray(ds, idtCorners, baseArray, nnear, vScale=1, majority=False):
    "Given the relevant information, builds the image array."

    Offset, Size = getOffsetSize(ds, idtCorners)
    IDT = getIDT(ds, Offset, Size, vScale)
    ImageArray = IDT(baseArray, nnear=nnear, eps=0.1, majority=majority)

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

def processTile(args, imagedir, tileRowIndex, tileColIndex):
    "Actually process a tile."
    tileShape = args.tile
    mult = args.mult
    vscale = args.vscale
    maxdepth = args.maxdepth
    slope = args.slope
    curtime = time()
    (lcds, elevds) = getDataset(args.region)
    (rows, cols) = getDatasetDims(args.region)
    maxRows = int(rows*mult)
    maxCols = int(cols*mult)
    baseOffset, baseSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols)
    idtOffset, idtSize = getTileOffsetSize(tileRowIndex, tileColIndex, tileShape, maxRows, maxCols, idtPad=16)
    print "Generating tile (%d, %d) with dimensions (%d, %d)..." % (tileRowIndex, tileColIndex, baseSize[0], baseSize[1])

    baseShape = (baseSize[1], baseSize[0])
    baseArray = getLatLongArray(lcds, baseOffset, baseSize, mult)

    # these points are scaled coordinates
    idtUL = getLatLong(lcds, int(idtOffset[0]/mult), int(idtOffset[1]/mult))
    idtLR = getLatLong(lcds, int((idtOffset[0]+idtSize[0])/mult), int((idtOffset[1]+idtSize[1])/mult))

    # nnear=1 for landcover, 11 for elevation
    lcImageArray = getImageArray(lcds, (idtUL, idtLR), baseArray, 11, majority=True)
    lcImageArray.resize(baseShape)

    # nnear=1 for landcover, 11 for elevation
    elevImageArray = getImageArray(elevds, (idtUL, idtLR), baseArray, 11, vscale)
    elevImageArray.resize(baseShape)

    # TODO: go through the arrays for some special transmogrification
    # first idea: bathymetry
    # TODO: fix this so it reads idtpadded data
    bathyImageArray = getBathymetry(lcImageArray, maxdepth, slope)
    
    # save images
    lcImage = Image.fromarray(lcImageArray)
    lcImage.save(os.path.join(imagedir, 'lc-%d-%d.gif' % (baseOffset[0], baseOffset[1])))
    lcImage = None
    elevImage = Image.fromarray(elevImageArray)
    elevImage.save(os.path.join(imagedir, 'elev-%d-%d.gif' % (baseOffset[0], baseOffset[1])))
    elevImage = None
    bathyImage = Image.fromarray(bathyImageArray)
    bathyImage.save(os.path.join(imagedir, 'bathy-%d-%d.gif' % (baseOffset[0], baseOffset[1])))
    bathyImage = None

    print '... done with (%d, %d) in %f seconds!' % (tileRowIndex, tileColIndex, (time()-curtime))

def processTilestar(args):
    return processTile(*args)

