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
        lcPercent = round((value*10000)/lcTotal)/100.0
        print '  %d (%.2f): %s' % (value, lcPercent, key)

# process an aggregate of given land cover value
def processTerrain(terrains):
    global lcTotal
    global lcCount
    columns = []
    for terrain in terrains:
        (lcval, x, z, elevval, bathyval) = terrain
        lcTotal += 1
        if (lcval not in lcType):
            print('unexpected value for land cover: ' + lcval)
            lcCount[0] += 1
            columns.append([x, z, elevval, 'Dirt'])
        else:
            if (lcval == 127):
                # no data!
                lcval = nodata
            lcCount[lcval] += 1
            # http://www.mrlc.gov/nlcd_definitions.php
            if (lcval == 11):
                columns.append([x, z, elevval, 'Sand', bathyval, 'Water'])
            elif (lcval == 12):
                columns.append([x, z, elevval, 'Sand', bathyval, 'Ice'])
            elif (lcval == 21):
                if (random() < 0.20):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 22):
                if (random() < 0.35):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 23):
                if (random() < 0.65):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 24):
                if (random() < 0.90):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 1, 0)
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 31):
                if (random() < 0.20):
                    blockType = 'Stone'
                else:
                    placeTree(x, z, elevval, 1, -1)
                    blockType = 'Sand'
                columns.append([x, z, elevval, 'Sand', 2, blockType])
            elif (lcval == 32):
                columns.append([x, z, elevval, 'Sand'])
            elif (lcval == 41):
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
                placeTree(x, z, elevval, 5, 2)
            elif (lcval == 42):
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
                placeTree(x, z, elevval, 5, 1)
            elif (lcval == 43):
                if (random() < 0.50):
                    treeType = 0
                else:
                    treeType = 1
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
                placeTree(x, z, elevval, 5, treeType)
            elif (lcval == 51):
                if (random() < 0.25):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 52):
                # FIXME: make shrubs?
                if (random() < 0.25):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 71):
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
            elif (lcval == 72):
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
            elif (lcval == 73):
                if (random() < 0.90):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 74):
                if (random() < 0.90):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 81):
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
            elif (lcval == 82):
                columns.append([x, z, elevval, 'Dirt', 1, 'Grass'])
            elif (lcval == 90):
                if (random() < 0.50):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 5, 1)
                else:
                    blockType = 'Water'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 91):
                if (random() < 0.50):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 5, 0)
                else:
                    blockType = 'Water'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 92):
                if (random() < 0.50):
                    blockType = 'Grass'
                else:
                    blockType = 'Water'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 93):
                if (random() < 0.50):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, 5, 2)
                else:
                    blockType = 'Water'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 94):
                if (random() < 0.50):
                    blockType = 'Grass'
                else:
                    blockType = 'Water'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 95):
                if (random() < 0.50):
                    blockType = 'Grass'
                else:
                    blockType = 'Water'
                columns.append([x, z, elevval, 'Dirt', 1, blockType])
            elif (lcval == 96):
                columns.append([x, z, elevval, 'Dirt', 1, 'Water'])
            elif (lcval == 97):
                columns.append([x, z, elevval, 'Dirt', 1, 'Water'])
            elif (lcval == 98):
                columns.append([x, z, elevval, 'Dirt', 1, 'Water'])
            elif (lcval == 99):
                columns.append([x, z, elevval, 'Dirt', 1, 'Water'])
            # we have a column and coordinates
            # we should make a big list and send it to a new layers()
    layers(columns)

# initialize
populateLandCoverVariables(lcType, lcCount)
