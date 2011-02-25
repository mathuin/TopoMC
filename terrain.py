# landcover module
from __future__ import division
from random import random, randint
from mcmap import layers
from tree import placeTree, treeProb, forestProb
from multinumpy import SharedMemArray
from numpy import zeros, int64
from multiprocessing import Value

# land cover constants
# (see http://www.epa.gov/mrlc/definitions.html among others)
# what portion of developed land should be stone versus grass
# 21: <20, 22: 20-49, 23: 50-79, 24: 80-100
level21stone = 0.10
level22stone = 0.35
level23stone = 0.65
level24stone = 0.90
# what portion of barren land should be stone versus sand
# no real values inferred
level31stone = 0.50
# forest: trees > 5m tall, canopy 25-100%
# what portion of mixed forest is deciduous versus evergreen
# 43: neither deciduous nor evergreen is greater than 75 percent
level43tree0 = 0.50
# shrubland: trees < 5m tall
level51stone = 0.25
level52stone = 0.25
level73stone = 0.90
level74stone = 0.90
# what percentage of wetlands should be grass (versus water)
wetlandsgrass = 0.80

# land cover statistics
# last two here need to be multiprocessor friendly
lcType = {
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
        127 : "No Data"
        }
lcCount = {}
for key in lcType.keys():
    lcCount[key] = Value('i', 0)
nodata = 11

def printLandCoverStatistics():
    lcTuples = [(lcType[index], lcCount[index].value) for index in lcCount.keys() if lcCount[index].value > 0]
    lcTotal = sum([lcTuple[1] for lcTuple in lcTuples])
    print 'Land cover statistics (%d total):' % lcTotal
    for key, value in sorted(lcTuples, key=lambda lc: lc[1], reverse=True):
        lcPercent = (value*100)/lcTotal
        print '  %d (%.2f%%): %s' % (value, lcPercent, key)

# process an aggregate of given land cover value
def processTerrain(terrains):
    columns = []
    for terrain in terrains:
        (lcval, x, z, elevval, bathyval, crustval) = terrain
        if (lcval not in lcType):
            print('unexpected value for land cover: %d' % lcval)
            lcCount[0].value += 1
            columns.append([x, z, elevval, crustval, 'Dirt'])
        else:
            if (lcval == 127):
                # the "no data" value
                lcval = nodata
            lcCount[lcval].value += 1
            # http://www.mrlc.gov/nlcd_definitions.php
            if (lcval == 11):
                newcrustval = int(max(0,crustval-(bathyval/2)))
                columns.append([x, z, elevval, newcrustval, 'Sand', bathyval, 'Water (still)'])
            elif (lcval == 12):
                newcrustval = int(max(0,crustval-(bathyval/2)))
                columns.append([x, z, elevval, newcrustval, 'Sand', bathyval-1, 'Water (still)', 1, 'Ice'])
            elif (lcval == 21):
                if (random() < level21stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Regular')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 22):
                if (random() < level22stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Regular')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 23):
                if (random() < level23stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Regular')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 24):
                if (random() < level24stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Regular')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 31):
                if (random() < level31stone):
                    blockType = 'Stone'
                else:
                    placeTree(x, z, elevval, treeProb, 'Cactus')
                    blockType = 'Sand'
                columns.append([x, z, elevval, crustval, 'Sand', 2, blockType])
            elif (lcval == 32):
                columns.append([x, z, elevval, crustval, 'Sand'])
            elif (lcval == 41):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
                placeTree(x, z, elevval, forestProb, 'Redwood')
            elif (lcval == 42):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
                placeTree(x, z, elevval, forestProb, 'Birch')
            elif (lcval == 43):
                if (random() < level43tree0):
                    treeType = 'Redwood'
                else:
                    treeType = 'Birch'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
                placeTree(x, z, elevval, forestProb, treeType)
            elif (lcval == 51):
                if (random() < level51stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Shrub')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 52):
                if (random() < level52stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Shrub')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 71):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
            elif (lcval == 72):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
            elif (lcval == 73):
                if (random() < level73stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Shrub')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 74):
                if (random() < level74stone):
                    blockType = 'Stone'
                else:
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Shrub')
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 81):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
            elif (lcval == 82):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Grass'])
            elif (lcval == 90):
                if (random() < wetlandsgrass):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, forestProb, 'Regular')
                else:
                    blockType = 'Water (still)'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 91):
                if (random() < wetlandsgrass):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, forestProb, 'Regular')
                else:
                    blockType = 'Water (still)'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 92):
                if (random() < wetlandsgrass):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Shrub')
                else:
                    blockType = 'Water (still)'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 93):
                if (random() < wetlandsgrass):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, forestProb, 'Regular')
                else:
                    blockType = 'Water (still)'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 94):
                if (random() < wetlandsgrass):
                    blockType = 'Grass'
                    placeTree(x, z, elevval, treeProb, 'Shrub')
                else:
                    blockType = 'Water (still)'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 95):
                if (random() < wetlandsgrass):
                    blockType = 'Grass'
                else:
                    blockType = 'Water (still)'
                columns.append([x, z, elevval, crustval, 'Dirt', 1, blockType])
            elif (lcval == 96):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Water (still)'])
            elif (lcval == 97):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Water (still)'])
            elif (lcval == 98):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Water (still)'])
            elif (lcval == 99):
                columns.append([x, z, elevval, crustval, 'Dirt', 1, 'Water (still)'])
    layers(columns)
