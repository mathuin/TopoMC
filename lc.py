# landcover module
from random import random, randint
from mcmap import layers
from tree import placeTree

# land cover statistics
lcType = {}
lcCount = {}
lcTotal = 0
nodata = 0

def populateLandCoverVariables(lcType, lcCount):
    # first add all the text values for land covers
    # http://www.mrlc.gov/nlcd_definitions.php
    lcMetaType = {
        0 : "Unknown",
	11 : "Water",
	12 : "Ice/Snow",
	21 : "Developed/Open-Space",
	22 : "Developed/Low-Intensity",
	23 : "Developed/Medium-Intensity",
	24 : "Developed/High-Intensity",
	31 : "Barren Land",
	32 : "Unconsolidated Shore",
	41 : "Deciduous Forest",
	42 : "Evergreen Forest",
	43 : "Mixed Forest",
	51 : "Dwarf Scrub",
	52 : "Shrub/Scrub",
	71 : "Grasslands/Herbaceous",
	72 : "Sedge/Herbaceous",
	73 : "Lichens",
	74 : "Moss",
	81 : "Pasture/Hay",
	82 : "Cultivated Crops",
	90 : "Woody Wetlands",
	91 : "Palustrine Forested Wetlands",
	92 : "Palustrine Scrub/Shrub Wetlands",
	93 : "Estuarine Forested Wetlands",
	94 : "Estuarine Scrub/Shrub Wetlands",
	95 : "Emergent Herbaceous Wetlands",
	96 : "Palustrine Emergent Wetlands",
	97 : "Estuarine Emergent Wetlands",
	98 : "Palustrine Aquatic Bed",
	99 : "Estuarine Aquatic Bed",
        127: "No Data"
        }
    
    for i in lcMetaType:
        lcType[i] = lcMetaType[i]
	lcCount[i] = 0
        

def printLandCoverStatistics():
    print 'Land cover statistics (%d total):' % lcTotal
    lcTuples = [(lcType[index], lcCount[index]) for index in lcCount if lcCount[index] > 0]
    for key, value in sorted(lcTuples, key=lambda lc: lc[1], reverse=True):
        #lcPercent = round((value*10000)/lcTotal)/100.0
        lcPercent = (value/lcTotal)*100
        print '  %d (%.2f): %s' % (value, lcPercent, key)

# process a given land cover value
def processLcval(lcval, x, z, elevval, bathyval):
    global lcTotal
    global lcCount
    lcTotal += 1
    if (lcval not in lcType):
        print('unexpected value for land cover: ' + lcval)
        lcCount[0] += 1
        layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt')
    else:
        if (lcval == 127):
            # no data!
            lcval = nodata
        lcCount[lcval] += 1
        # http://www.mrlc.gov/nlcd_definitions.php
        if (lcval == 11):
            # water
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand', bathyval, 'Water')
        elif (lcval == 12):
            # ice
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand', bathyval, 'Ice')
        elif (lcval == 21):
            # developed/open-space (20% stone 80% grass rand tree)
            if (random() < 0.20):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, 1, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 22):
            # developed/open-space (35% stone 65% grass rand tree)
            if (random() < 0.35):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, 1, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 23):
            # developed/open-space (65% stone 35% grass rand tree)
            if (random() < 0.65):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            placeTree(x, z, elevval, 1, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 24):
            # developed/open-space (90% stone 10% grass rand tree)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
                placeTree(x, z, elevval, 1, 0)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 31):
            # barren land (baseline% sand baseline% stone)
            if (random() < 0.20):
                blockType = 'Stone'
            else:
                placeTree(x, z, elevval, 1, -1)
                blockType = 'Sand'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand', 2, blockType)
        elif (lcval == 32):
            # unconsolidated shore (sand)	 
            layers(x, z, elevval, 'Stone', randint(5,7), 'Sand')
        elif (lcval == 41):
            # deciduous forest (grass with tree #1)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, 5, 2)
        elif (lcval == 42):
            # evergreen forest (grass with tree #2)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, 5, 1)
        elif (lcval == 43):
            # mixed forest (grass with either tree)
            if (random() < 0.50):
                treeType = 0
            else:
                treeType = 1
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
            placeTree(x, z, elevval, 5, treeType)
        elif (lcval == 51):
            # dwarf scrub (grass with 25% stone)
            if (random() < 0.25):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 52):
            # shrub/scrub (grass with 25% stone)
            # FIXME: make shrubs?
            if (random() < 0.25):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 71):
            # grasslands/herbaceous
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 72):
            # sedge/herbaceous
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 73):
            # lichens (90% stone 10% grass)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 74):
            # moss (90% stone 10% grass)
            if (random() < 0.90):
                blockType = 'Stone'
            else:
                blockType = 'Grass'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 81):
            # pasture/hay
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 82):
            # cultivated crops
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Grass')
        elif (lcval == 90):
            # woody wetlands (grass with rand trees and -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, 5, 1)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 91):
            # palustrine forested wetlands
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, 5, 0)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 92):
            # palustrine scrub/shrub wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 93):
            # estuarine forested wetlands (grass with rand trees and water)
            if (random() < 0.50):
                blockType = 'Grass'
                placeTree(x, z, elevval, 5, 2)
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 94):
            # estuarine scrub/shrub wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 95):
            # emergent herbaceous wetlands (grass with baseline% -1m water)
            if (random() < 0.50):
                blockType = 'Grass'
            else:
                blockType = 'Water'
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, blockType)
        elif (lcval == 96):
            # palustrine emergent wetlands-persistent (-1m water?)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')
        elif (lcval == 97):
            # estuarine emergent wetlands (-1m water)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')
        elif (lcval == 98):
            # palustrine aquatic bed (-1m water)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')
        elif (lcval == 99):
            # estuarine aquatic bed (-1m water)
            layers(x, z, elevval, 'Stone', randint(5,7), 'Dirt', 1, 'Water')

# process an aggregate of given land cover value
def processLcvals(lcvals):
    global lcTotal
    global lcCount
    for elem in lcvals:
        (lcval, x, z, elevval, bathyval) = elem
        lcTotal += 1
        if (lcval not in lcType):
            print('unexpected value for land cover: ' + lcval)
            lcCount[0] += 1
            column = ('Dirt')
        else:
            if (lcval == 127):
                # no data!
                lcval = nodata
            lcCount[lcval] += 1
            # http://www.mrlc.gov/nlcd_definitions.php
            if (lcval == 11):
                column = ('Sand', bathyval, 'Water')
            elif (lcval == 12):
                column = ('Sand', bathyval, 'Ice')
            elif (lcval == 21):
                if (random() < 0.20):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                column = ('Dirt', 1, blockType)
            elif (lcval == 22):
                if (random() < 0.35):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                column = ('Dirt', 1, blockType)
            elif (lcval == 23):
                if (random() < 0.65):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                column = ('Dirt', 1, blockType)
            elif (lcval == 24):
                if (random() < 0.90):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                column = ('Dirt', 1, blockType)
            elif (lcval == 31):
                if (random() < 0.20):
                    blockType = 'Stone'
                else:
                    placeTree(x, z, elevval, 1, -1)
                    blockType = 'Sand'
                column = ('Sand', 2, blockType)
            elif (lcval == 32):
                column = ('Sand')
            elif (lcval == 41):
                column = ('Dirt', 1, 'Grass')
                placeTree(x, z, elevval, 5, 2)
            elif (lcval == 42):
                column = ('Dirt', 1, 'Grass')
                placeTree(x, z, elevval, 5, 1)
            elif (lcval == 43):
                if (random() < 0.50):
                    treeType = 0
                else:
                    treeType = 1
                column = ('Dirt', 1, 'Grass')
                placeTree(x, z, elevval, 5, treeType)
            elif (lcval == 51):
                if (random() < 0.25):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                column = ('Dirt', 1, blockType)
            elif (lcval == 52):
                # FIXME: make shrubs?
                if (random() < 0.25):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                column = ('Dirt', 1, blockType)
            elif (lcval == 71):
                column = ('Dirt', 1, 'Grass')
            elif (lcval == 72):
                column = ('Dirt', 1, 'Grass')
            elif (lcval == 73):
                if (random() < 0.90):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                column = ('Dirt', 1, blockType)
            elif (lcval == 74):
                if (random() < 0.90):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                column = ('Dirt', 1, blockType)
            elif (lcval == 81):
                column = ('Dirt', 1, 'Grass')
            elif (lcval == 82):
                column = ('Dirt', 1, 'Grass')
            elif (lcval == 90):
                if (random() < 0.50):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 5, 1)
                else:
                    blockType = 'Water'
                column = ('Dirt', 1, blockType)
            elif (lcval == 91):
                if (random() < 0.50):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 5, 0)
                else:
                    blockType = 'Water'
                column = ('Dirt', 1, blockType)
            elif (lcval == 92):
                if (random() < 0.50):
                    blockType = 'Grass'
                else:
                    blockType = 'Water'
                column = ('Dirt', 1, blockType)
            elif (lcval == 93):
                if (random() < 0.50):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 5, 2)
                else:
                    blockType = 'Water'
                column = ('Dirt', 1, blockType)
            elif (lcval == 94):
                if (random() < 0.50):
                    blockType = 'Grass'
                else:
                    blockType = 'Water'
                column = ('Dirt', 1, blockType)
            elif (lcval == 95):
                if (random() < 0.50):
                    blockType = 'Grass'
                else:
                    blockType = 'Water'
                column = ('Dirt', 1, blockType)
            elif (lcval == 96):
                column = ('Dirt', 1, 'Water')
            elif (lcval == 97):
                column = ('Dirt', 1, 'Water')
            elif (lcval == 98):
                column = ('Dirt', 1, 'Water')
            elif (lcval == 99):
                column = ('Dirt', 1, 'Water')
            # we have a column and coordinates
            # we should make a big list and send it to a new layers()

# initialize
populateLandCoverVariables(lcType, lcCount)
