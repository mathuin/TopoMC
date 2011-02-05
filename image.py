# image module
import re
import os
import operator
import Image
from numpy import asarray
from time import clock
from lc import processLcval
from mcmap import maxelev
from multiprocessing import Pool
from itertools import product

# paths for images
imagesPaths = ['Images']

# functions
def getImagesDict(imagepaths):
    "Given a list of paths, generate a dict of imagesets."
    # FIXME: check to see that images are 'complete' and report back sizes.
    # i.e., check names and dimensions

    imagere = re.compile(r'^(\w+)-(\d+)-(\d+).gif')

    imagedirs = {}
    imagesets = {}
    imagedims = {}
    for imagepath in imagepaths:
        regions = [ name for name in os.listdir(imagepath) if os.path.isdir(os.path.join(imagepath, name)) ]
        for region in regions:
            tmpis = {'lc': [], 'elev': [], 'bathy': []}
            imageregion = os.path.join(imagepath, region)
            for imagefile in os.listdir(imageregion):
                (filetype, offset_x, offset_z) = imagere.search(imagefile).groups()
                if (filetype in tmpis.keys()):
                    img = Image.open(os.path.join(imageregion, imagefile))
                    ary = asarray(img)
                    (size_z, size_x) = ary.shape
                    img = None
                    ary = None
                    newelem = ((int(offset_x), int(offset_z)), (int(size_x), int(size_z))) 
                    tmpis[filetype].append(newelem)
            # lazy man will look for largest file and add the coordinates
            # clever man will verify that all files are present
            tmpid = {'lc': [], 'elev': [], 'bathy': []}
            for key in tmpid.keys():
                indexoffset = operator.itemgetter(0)
                tmpis[key].sort(key=indexoffset)
                lastent = tmpis[key][-1]
                tmpid[key] = (lastent[0][0]+lastent[1][0], lastent[0][1]+lastent[1][1])
            if (set(tmpis['lc']) == set(tmpis['elev']) and 
                set(tmpis['lc']) == set(tmpis['bathy']) and 
                set(tmpid['lc']) == set(tmpid['elev']) and 
                set(tmpid['lc']) == set(tmpid['bathy'])):
                imagedirs[region] = os.path.join(imagepath, region)
                imagesets[region] = tmpis['lc']
                imagedims[region] = tmpid['lc']

    return imagedirs, imagesets, imagedims

def listImagesets():
    "List all the available imagesets, including dimensions."
    print 'Valid imagesets detected:'
    print "\n".join(["\t%s:\n\t\t%d tiles (%d, %d)" % (region, len(imageSets[region]), imageDims[region][0], imageDims[region][1]) for region in imageDirs])

def checkImageset(string):
    "Checks to see if there are images for this imageset."
    if (string != None and not string in imageDirs):
        listImagesets(imageDirs)
        argparse.error("%s is not a valid imageset" % string)
    return string

def processImage(region, offset_x, offset_z):
    imagetime = clock()

    imgtemp = '%s/%%s-%d-%d.gif' % (region, offset_x, offset_z)
    lcimg = Image.open(imgtemp % 'lc')
    elevimg = Image.open(imgtemp % 'elev')
    bathyimg = Image.open(imgtemp % 'bathy')

    lcarray = asarray(lcimg)
    elevarray = asarray(elevimg)
    bathyarray = asarray(bathyimg)

    lcimg = None
    elevimg = None
    bathyimg = None

    # gotta start somewhere!
    localmax = 0
    spawnx = 10
    spawnz = 10

    # inform the user
    print 'Processing tile at position (%d, %d)...' % (offset_x, offset_z)
    (size_z, size_x) = lcarray.shape

    # iterate over the image
    for x,z in product(xrange(size_x), xrange(size_z)):
        lcval = lcarray[z,x]
        elevval = elevarray[z,x]
        bathyval = bathyarray[z,x]
        real_x = offset_x + x
        real_z = offset_z + z
        if (elevval > maxelev):
            print 'warning: elevation %d exceeds maximum elevation (%d)' % (elevval, maxelev)
            elevval = maxelev
        if (elevval > localmax):
            localmax = elevval
            spawnx = real_x
            spawnz = real_z
        processLcval(lcval, real_x, real_z, elevval, bathyval)
	
    lcarray = None
    elevarray = None
    bathyarray = None

    # print out status
    print '... finished in %.2f seconds.' % (clock()-imagetime)

    return (spawnx, spawnz, localmax)

# pointer function used for multiprocessing
def processImagestar(args):
    return processImage(*args)

def processImages(region, processes):
    # FIXME: not multiprocessor friendly (problem with processLcvar?)
    if (processes == 1 or True):
        peaks = [processImage(imageDirs[region], offset[0], offset[1]) for (offset, size) in imageSets[region]]
    else:
        pool = Pool(processes)
        tasks = [(imageDirs[region], offset[0], offset[1]) for (offset, size) in imageSets[region]]
        results = pool.imap_unordered(processImagestar, tasks)
        peaks = [x for x in results]
    return peaks

# initialize variables
imageDirs, imageSets, imageDims = getImagesDict(imagesPaths)

if __name__ == '__main__':
    listImagesets(imageDirs)
