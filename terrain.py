# landcover module
from random import random, randint
from mcmap import layers
from tree import placeTree
from multinumpy import SharedMemArray
from numpy import zeros, int32
from multiprocessing import Value

# land cover statistics
# last two here need to be multiprocessor friendly
lcType = {
        0 : "Unknown",
        # 1 : "Unused", 
        # 2 : "Unused", 
        # 3 : "Unused", 
        # 4 : "Unused", 
        # 5 : "Unused", 
        # 6 : "Unused", 
        # 7 : "Unused", 
        # 8 : "Unused", 
        # 9 : "Unused", 
        # 10 : "Unused",
	11 : "Water",
	12 : "Ice/Snow",
        # 13 : "Unused", 
        # 14 : "Unused", 
        # 15 : "Unused", 
        # 16 : "Unused", 
        # 17 : "Unused", 
        # 18 : "Unused", 
        # 19 : "Unused", 
        # 20 : "Unused",
	21 : "Developed/Open-Space",
	22 : "Developed/Low-Intensity",
	23 : "Developed/Medium-Intensity",
	24 : "Developed/High-Intensity",
        # 25 : "Unused", 
        # 26 : "Unused", 
        # 27 : "Unused", 
        # 28 : "Unused", 
        # 29 : "Unused", 
        # 30 : "Unused",
	31 : "Barren Land",
	32 : "Unconsolidated Shore",
        # 33 : "Unused", 
        # 34 : "Unused", 
        # 35 : "Unused", 
        # 36 : "Unused", 
        # 37 : "Unused", 
        # 38 : "Unused", 
        # 39 : "Unused", 
        # 40 : "Unused",
	41 : "Deciduous Forest",
	42 : "Evergreen Forest",
	43 : "Mixed Forest",
        # 44 : "Unused", 
        # 45 : "Unused", 
        # 46 : "Unused", 
        # 47 : "Unused", 
        # 48 : "Unused", 
        # 49 : "Unused", 
        # 50 : "Unused",
	51 : "Dwarf Scrub",
	52 : "Shrub/Scrub",
        # 53 : "Unused", 
        # 54 : "Unused", 
        # 55 : "Unused", 
        # 56 : "Unused", 
        # 57 : "Unused", 
        # 58 : "Unused", 
        # 59 : "Unused", 
        # 60 : "Unused",
        # 61 : "Unused", 
        # 62 : "Unused", 
        # 63 : "Unused", 
        # 64 : "Unused", 
        # 65 : "Unused", 
        # 66 : "Unused", 
        # 67 : "Unused", 
        # 68 : "Unused", 
        # 69 : "Unused", 
        # 70 : "Unused",
	71 : "Grasslands/Herbaceous",
	72 : "Sedge/Herbaceous",
	73 : "Lichens",
	74 : "Moss",
        # 75 : "Unused", 
        # 76 : "Unused", 
        # 77 : "Unused", 
        # 78 : "Unused", 
        # 79 : "Unused", 
        # 80 : "Unused",
	81 : "Pasture/Hay",
	82 : "Cultivated Crops",
        # 82 : "Unused", 
        # 83 : "Unused", 
        # 84 : "Unused", 
        # 85 : "Unused", 
        # 86 : "Unused", 
        # 87 : "Unused", 
        # 88 : "Unused", 
        # 89 : "Unused", 
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
        # 100 : "Unused",
        # 101 : "Unused", 
        # 102 : "Unused", 
        # 103 : "Unused", 
        # 104 : "Unused", 
        # 105 : "Unused", 
        # 106 : "Unused", 
        # 107 : "Unused", 
        # 108 : "Unused", 
        # 109 : "Unused", 
        # 110 : "Unused",
        # 111 : "Unused", 
        # 112 : "Unused", 
        # 113 : "Unused", 
        # 114 : "Unused", 
        # 115 : "Unused", 
        # 116 : "Unused", 
        # 117 : "Unused", 
        # 118 : "Unused", 
        # 119 : "Unused", 
        # 120 : "Unused",
        # 121 : "Unused", 
        # 122 : "Unused", 
        # 123 : "Unused", 
        # 124 : "Unused", 
        # 125 : "Unused", 
        # 126 : "Unused", 
        127 : "No Data"
        # 128 : "Unused", 
        # 129 : "Unused", 
        # 130 : "Unused",
        # 131 : "Unused", 
        # 132 : "Unused", 
        # 133 : "Unused", 
        # 134 : "Unused", 
        # 135 : "Unused", 
        # 136 : "Unused", 
        # 137 : "Unused", 
        # 138 : "Unused", 
        # 139 : "Unused", 
        # 140 : "Unused",
        # 141 : "Unused", 
        # 142 : "Unused", 
        # 143 : "Unused", 
        # 144 : "Unused", 
        # 145 : "Unused", 
        # 146 : "Unused", 
        # 147 : "Unused", 
        # 148 : "Unused", 
        # 149 : "Unused", 
        # 150 : "Unused",
        # 151 : "Unused", 
        # 152 : "Unused", 
        # 153 : "Unused", 
        # 154 : "Unused", 
        # 155 : "Unused", 
        # 156 : "Unused", 
        # 157 : "Unused", 
        # 158 : "Unused", 
        # 159 : "Unused", 
        # 160 : "Unused",
        # 161 : "Unused", 
        # 162 : "Unused", 
        # 163 : "Unused", 
        # 164 : "Unused", 
        # 165 : "Unused", 
        # 166 : "Unused", 
        # 167 : "Unused", 
        # 168 : "Unused", 
        # 169 : "Unused", 
        # 170 : "Unused",
        # 171 : "Unused", 
        # 172 : "Unused", 
        # 173 : "Unused", 
        # 174 : "Unused", 
        # 175 : "Unused", 
        # 176 : "Unused", 
        # 177 : "Unused", 
        # 178 : "Unused", 
        # 179 : "Unused", 
        # 180 : "Unused",
        # 181 : "Unused", 
        # 182 : "Unused", 
        # 183 : "Unused", 
        # 184 : "Unused", 
        # 185 : "Unused", 
        # 186 : "Unused", 
        # 187 : "Unused", 
        # 188 : "Unused", 
        # 189 : "Unused", 
        # 190 : "Unused",
        # 191 : "Unused", 
        # 192 : "Unused", 
        # 193 : "Unused", 
        # 194 : "Unused", 
        # 195 : "Unused", 
        # 196 : "Unused", 
        # 197 : "Unused", 
        # 198 : "Unused", 
        # 199 : "Unused", 
        # 200 : "Unused",
        # 201 : "Unused", 
        # 202 : "Unused", 
        # 203 : "Unused", 
        # 204 : "Unused", 
        # 205 : "Unused", 
        # 206 : "Unused", 
        # 207 : "Unused", 
        # 208 : "Unused", 
        # 209 : "Unused", 
        # 210 : "Unused",
        # 211 : "Unused", 
        # 212 : "Unused", 
        # 213 : "Unused", 
        # 214 : "Unused", 
        # 215 : "Unused", 
        # 216 : "Unused", 
        # 217 : "Unused", 
        # 218 : "Unused", 
        # 219 : "Unused", 
        # 220 : "Unused",
        # 221 : "Unused", 
        # 222 : "Unused", 
        # 223 : "Unused", 
        # 224 : "Unused", 
        # 225 : "Unused", 
        # 226 : "Unused", 
        # 227 : "Unused", 
        # 228 : "Unused", 
        # 229 : "Unused", 
        # 230 : "Unused",
        # 231 : "Unused", 
        # 232 : "Unused", 
        # 233 : "Unused", 
        # 234 : "Unused", 
        # 235 : "Unused", 
        # 236 : "Unused", 
        # 237 : "Unused", 
        # 238 : "Unused", 
        # 239 : "Unused", 
        # 240 : "Unused",
        # 241 : "Unused", 
        # 242 : "Unused", 
        # 243 : "Unused", 
        # 244 : "Unused", 
        # 245 : "Unused", 
        # 246 : "Unused", 
        # 247 : "Unused", 
        # 248 : "Unused", 
        # 249 : "Unused", 
        # 250 : "Unused",
        # 251 : "Unused", 
        # 252 : "Unused", 
        # 253 : "Unused", 
        # 254 : "Unused", 
        # 255 : "Unused" 
        }
lcCount = SharedMemArray(zeros((256),dtype=int32))
lcTotal = Value('i', 0)
nodata = 0

def printLandCoverStatistics():
    print 'Land cover statistics (%d total):' % lcTotal.value
    lcCountArr = lcCount.asarray()
    lcTuples = [(lcType[index], lcCountArr[index]) for index in lcCountArr]
    for key, value in sorted(lcTuples, key=lambda lc: lc[1], reverse=True):
        if value > 0:
            lcPercent = round((value*10000)/lcTotal.value)/100.0
            print '  %d (%.2f%%): %s' % (value, lcPercent, key)

# process an aggregate of given land cover value
def processTerrain(terrains):
    columns = []
    lcCountArr = lcCount.asarray()
    for terrain in terrains:
        (lcval, x, z, elevval, bathyval) = terrain
        lcTotal.value += 1
        if (lcval not in lcType):
            print('unexpected value for land cover: ' + lcval)
            lcCountArr[0] += 1
            columns.append([x, z, elevval, 'Dirt'])
        else:
            if (lcval == 127):
                # no data!
                lcval = nodata
            lcCountArr[lcval] += 1
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
