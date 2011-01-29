// constants
var sealevel = 64;
var baseline = 32; // below here is just stone
var filler = sealevel - baseline;

// set maxMapHeight to a conservative value
var maxMapHeight = 125 - sealevel;

// these are outside the loop
// processImage modifies these as it runs
var maxelev = 0;
var spawnx = 0;
var spawny = sealevel;
var spawnz = 0;

// what region are we doing?
var region = 'BlockIsland';
//var region = 'Hamilton';
var imagedir = "Images/"+region;
// FIXME: these should have defaults to "all files" eventually
var minrows = 0;
var mincols = 0;
var maxrows = 1520;
var maxcols = 1990;
//var minrows = 512;
//var mincols = 512;
//var maxrows = 1535;
//var maxcols = 1535;
// tiling constants - also hopefully eventually optional
var tilerows = 256;
var tilecols = 256;

// land cover statistics
var lcType = {};
var lcCount = {};
var lcTotal = 0;
var treeType = {};
var treeCount = {};
var treeTotal = 0;

// land cover constants
var treeProb = 0.001;

// inside the loop
function processImage(offset_x, offset_z) {
    var lcimg = JCraft.Components.Images.Load(imagedir+"/lc-"+offset_x+"-"+offset_z+".gif");
    var elevimg = JCraft.Components.Images.Load(imagedir+"/elev-"+offset_x+"-"+offset_z+".gif");
    var size_x = lcimg.width;
    var size_z = lcimg.height;
    var stop_x = offset_x+size_x;
    var stop_z = offset_z+size_z;
    var imageDate = new Date();
    var startTime = imageDate.getTime();

    // inform the user
    print('Processing tile at position ('+offset_x+','+offset_z+')...');

    // iterate over the image
    for (var x = 0; x < size_x; x++) for (var z = 0; z < size_z; z++) {
	var flatindex = (z * size_x) + x;
	var lcval = lcimg[flatindex];
	var elevval = elevimg[flatindex];
	var real_x = offset_x + x;
	var real_z = offset_z + z;
	if (elevval > maxMapHeight) {
	    print('oh no elevation ' + elevval + ' is too high');
	    elevval = maxMapHeight;
	}
	if (elevval > maxelev) {
	    maxelev = elevval;
	    spawnx = real_x;
	    spawnz = real_z;
	    spawny = sealevel+elevval;
	}
	processLcval(lcval, real_x, real_z, elevval);
    }
	
    // print out status
    imageDate = new Date();
    var endTime = imageDate.getTime();
    var imageDelta = Math.round(endTime - startTime)/1000;
    print('... finished in ' + imageDelta + ' seconds.');
}

function populateLandCoverVariables(lcType, lcCount, treeType, treeCount) {
    // first add all the text values for land covers
    var lcMetaType = {
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
	99 : "Estuarine Aquatic Bed"
    };
    for (var i in lcMetaType) {
	lcType[i] = lcMetaType[i];
	lcCount[i] = 0;
    }
    // index starts with zero, cactus is -1
    var treeMetaType = {
	0 : "cactus",
	1 : "regular",
	2 : "redwood",
	3 : "birch"
    };
    for (var i in treeMetaType) {
	treeType[i] = treeMetaType[i];
	treeCount[i] = 0;
    }
}

// process a given land cover value
function processLcval(lcval, x, z, elevval) {
    var thisblock; // scratch space
    lcTotal++;
    if (!(lcval in lcType)) {
	print('unexpected value for land cover: ' + lcval);
	lcCount[0]++;
	layers(x, z, elevval, blockTypes.Dirt);
    } else {
	lcCount[lcval]++;
	switch(lcval) {
	case 11:
	    // water 2m over sand
	    // IDEA: survey neighboring squares
	    // if at least one is not water, use 1m, not 2m
	    layers(x, z, elevval, blockTypes.Sand, 2, blockTypes.Water);
	    break;
	case 12:
	    // ice
	    // FIXME: how to put ice on?
	    layers(x, z, elevval, blockTypes.Sand, 2, blockTypes.Ice);
	    break;
	case 21:
	    // developed/open-space (20% stone 80% grass rand tree)
	    if (Math.random() < 0.20) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
		// FIXME: regular trees for now
		placeTree(x, z, elevval, treeProb, 0);
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 22:
	    // developed/open-space (35% stone 65% grass rand tree)
	    if (Math.random() < 0.35) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
		// FIXME: regular trees for now
		placeTree(x, z, elevval, treeProb, 0);
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 23:
	    // developed/open-space (65% stone 35% grass rand tree)
	    if (Math.random() < 0.65) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
		// FIXME: regular trees for now
		placeTree(x, z, elevval, treeProb, 0);
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 24:
	    // developed/open-space (90% stone 10% grass rand tree)
	    if (Math.random() < 0.90) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
		// FIXME: regular trees for now
		placeTree(x, z, elevval, treeProb, 0);
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 31:
	    // barren land (baseline% sand baseline% stone)
	    if (Math.random() < 0.20) {
		thisblock = blockTypes.Stone;
	    } else {
		placeTree(x, z, elevval, treeProb, -1);
		thisblock = blockTypes.Sand;
	    }
	    layers(x, z, elevval, blockTypes.Sand, 2, thisblock);
	    break;
	case 32:
	    // unconsolidated shore (sand)	 
	    layers(x, z, elevval, blockTypes.Sand);
	    break;
	case 41:
	    // deciduous forest (grass with tree #1)
	    // it's a forest, more trees
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    placeTree(x, z, elevval, treeProb*5, 2);
	    break;
	case 42:
	    // evergreen forest (grass with tree #2)
	    // it's a forest, more trees
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    placeTree(x, z, elevval, treeProb*5, 1);
	    break;
	case 43:
	    // mixed forest (grass with either tree)
	    if (Math.random() < 0.50) {
		thisblock = 0;
	    } else {
		thisblock = 1;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    // it's a forest, more trees
	    placeTree(x, z, elevval, treeProb*5, thisblock);
	    break;
	case 51:
	    // dwarf scrub (grass with 25% stone)
	    if (Math.random() < 0.25) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 52:
	    // shrub/scrub (grass with 25% stone)
	    if (Math.random() < 0.25) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
	    }
	    // FIXME: make shrubs?
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 71:
	    // grasslands/herbaceous
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    break;
	case 72:
	    // sedge/herbaceous
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    break;
	case 73:
	    // lichens (90% stone 10% grass)
	    if (Math.random() < 0.90) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 74:
	    // moss (90% stone 10% grass)
	    if (Math.random() < 0.90) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 81:
	    // pasture/hay
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    break;
	case 82:
	    // cultivated crops
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    break;
	case 90:
	    // woody wetlands (grass with rand trees and -1m water)
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
		// woody wetlands, like a forest
		placeTree(x, z, elevval, treeProb*5, 1);
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 91:
	    // palustrine forested wetlands
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
		// "forested"
		placeTree(x, z, elevval, treeProb*5, 0);
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 92:
	    // palustrine scrub/shrub wetlands (grass with baseline% -1m water)
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 93:
	    // estuarine forested wetlands (grass with rand trees and water)
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
		// "forested""
		placeTree(x, z, elevval, treeProb*5, 2);
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 94:
	    // estuarine scrub/shrub wetlands (grass with baseline% -1m water)
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 95:
	    // emergent herbaceous wetlands (grass with baseline% -1m water)
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 96:
	    // palustrine emergent wetlands-persistent (-1m water?)
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Water);
	    break;
	case 97:
	    // estuarine emergent wetlands (-1m water)
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Water);
	    break;
	case 98:
	    // palustrine aquatic bed (-1m water)
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Water);
	    break;
	case 99:
	    // estuarine aquatic bed (-1m water)
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Water);
	    break;
	}
    }
}

// fills a column with layers of stuff
function layers() {
    // mandatory arguments
    var layersDate = new Date();
    var startTime = layersDate.getTime();
    var endTime;
    var myargs = Array.prototype.slice.call(arguments).reverse();
    var x = myargs.pop();
    var z = myargs.pop();
    var elevval = myargs.pop();
    var bottom = baseline;
    var top = sealevel+elevval;
    var slice = 0;

    // examples:
    // layers(x, y, elevval, blockType.Stone);
    //  - fill everything from baseline to elevval with stone
    // layers(x, y, elevval, blockType.Dirt, 2, blockType.Water);
    //  - elevval down two levels of water, rest dirt
    // layers(x, y, elevval, blockType.Stone, 1, blockType.Dirt, 1, blockType.Grass);
    //  - elevval down one level of water, then one level of dirt, then stone
    var data = myargs.reverse();
    do {
	// better be a block
	block = data.pop();
	if (myargs.length > 0) {
	    slice = data.pop();
	} else {
	    slice = top - bottom;
	}
	// now do something
	map.fillBlocks(x, 1, top-slice, slice, z, 1, block);
	top -= slice;
    } while (data.length > 0);
}

// generates random numbers from min to max (inclusive?)
function random(min, max) {
    return Math.floor(Math.random()*(max-min))+min;
}

// places leaves and tree
function makeTree(x, z, elevval, height, type) {
    // print('Placing a '+treeType[type]+' tree of height '+height+' at '+x+', '+z+', '+elevval+'...');
    // -1 = cactus, 0 = regular, 1 = redwood, 2 = birch
    var maxleafheight = height+1;
    var trunkheight = 2;
    for (var index = 0; index < maxleafheight; index++) {
	var y = sealevel+elevval+index;
	if (type == -1) {
	    map.setBlock(x, y, z, blockTypes.Cactus);
	    map.setBlock(x, y+1, z, blockTypes.Cactus);
	    map.setBlock(x, y+2, z, blockTypes.Cactus);
	    break;
	}
	if (index > trunkheight) {
	    var curleafwidth;
	    var curleafheight = index-trunkheight;
	    var totop = (maxleafheight-trunkheight)-curleafheight;
	    if (curleafheight > totop) {
		curleafwidth = totop+1;
	    } else {
		curleafwidth = curleafheight;
	    }
	    var xminleaf = x - curleafwidth;
	    var xmaxleaf = x + curleafwidth;
	    var zminleaf = z - curleafwidth;
	    var zmaxleaf = z + curleafwidth;
	    for (var xindex = xminleaf; xindex <= xmaxleaf; xindex++) 
		for (var zindex = zminleaf; zindex <= zmaxleaf; zindex++) {
		    map.setBlock(xindex, y, zindex, blockTypes.Leaves);
	     	    map.setBlockData(xindex, y, zindex, type);
	    }
	}
	if (index < height) {
	    map.setBlock(x, y, z, blockTypes.Log);
	    map.setBlockData(x, y, z, type);
	}
    }
    // increment tree count
    treeCount[type+1]++;
    treeTotal++;
}

function placeTree(x, z, elevval, prob, treeType) {
    var height;
    var chance = Math.random();
    if (chance < prob) {
	switch(treeType) {
	case -1:
	    // cactus
	    height = 3;
	    break;
	case 0:
	    // regular
	    height = random(4, 6);
	    break;
	case 1:
	    // redwood
	    height = random(10, 12);
	    break;
	case 2:
	    // birch
	    height = random(7, 9);
	    break;
	}
	makeTree(x, z, elevval, height, treeType);
    }
}

// everything an explorer needs, for now
function equipPlayer() {
    map.playerInventory.Add(new Item(itemTypes.IronSword));
    map.playerInventory.Add(new Item(itemTypes.IronPickaxe));
    map.playerInventory.Add(new Item(itemTypes.IronShovel));
    map.playerInventory.Add(new Item(itemTypes.IronAxe));
    map.playerInventory.AddAt(new Item(blockTypes.Torch), 8);
    var sandstack = new Item(blockTypes.Sand);
    sandstack.Count = 64;
    map.playerInventory.AddAt(sandstack, 7);
}

function printLandCoverStatistics(lcType, lcCount) {
    var lcB = [];
    var treeB = [];
    print('Land cover statistics ('+lcTotal+' total):');
    for (var lcIndex in lcCount)
	lcB.push({v: lcIndex, c: lcCount[lcIndex]});
    lcB.sort(function (a, b) { return b.c - a.c; });
    for (var lcElement in lcB) {
	var lcBev = lcB[lcElement].v;
    	if (lcCount[lcBev] > 0) {
	    var lcPercent = Math.round((lcCount[lcBev]*10000)/lcTotal)/100.0;
	    print('  '+lcCount[lcBev]+' ('+lcPercent+'%): '+lcType[lcBev]);
    	}
    }
    print('Tree statistics ('+treeTotal+' total):');
    for (var treeIndex in treeCount)
	treeB.push({v: treeIndex, c: treeCount[treeIndex]});
    treeB.sort(function (a, b) { return b.c - a.c; });
    for (var treeElement in treeB) {
	var treeBev = treeB[treeElement].v;
    	if (treeCount[treeBev] > 0) {
	    var treePercent = Math.round((treeCount[treeBev]*10000)/treeTotal)/100.0;
	    print('  '+treeCount[treeBev]+' ('+treePercent+'%): '+treeType[treeBev]);
    	}
    }
}

function main() {
    var mainDate = new Date();
    var startTime = mainDate.getTime();

    // what are we doing?
    print('Creating world from region '+region);

    // initialize the land cover variables
    populateLandCoverVariables(lcType, lcCount, treeType, treeCount);

    // for loop time!
    // first make sure that minrows and mincols start on tile boundaries
    minrows -= (minrows % tilerows);
    mincols -= (mincols % tilecols);
    for (var row = minrows; row < maxrows; row += tilerows) {
    	for (var col = mincols; col < maxcols; col += tilecols) {
    	    processImage(row, col);
    	}
    }

    // maximum elevation
    print('Maximum elevation: ' + maxelev);

    // set player position and spawn point (in this case, equal)
    print('Setting spawn values: ' + spawnx + ', ' + spawny + ', ' + spawnz);
    map.spawn = { x: spawnx, y: spawny+2, z: spawnz };
    map.playerLocation = map.spawn;

    printLandCoverStatistics(lcType, lcCount, treeType, treeCount);

    equipPlayer();

    mainDate = new Date();
    var endTime = mainDate.getTime();
    var mainDelta = Math.round(endTime - startTime)/1000;
    print('Processing done -- took ' + mainDelta + ' seconds.');
}

// hey ho let's go
main();
