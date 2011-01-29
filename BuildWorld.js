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
var spawny = 0;
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

// land cover constants
var treeProb = 0.00001;

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

    // fill bottom of this particular range with bedrock
    map.fillBlocks(offset_x, stop_x, 0, 1, offset_z, stop_z, blockTypes.Bedrock);

    // fill middle chunk of this particular range with stone
    map.fillBlocks(offset_x, stop_x, 1, baseline, offset_z, stop_z, blockTypes.Stone);

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

function populateLandCoverVariables(lcType, lcCount) {
    // first add all the text values for land covers
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
	99 : "Estuarine Aquatic Bed"
    };
    for (var i in lcMetaType) {
	lcType[i] = lcMetaType[i];
	lcCount[i] = 0;
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
		place_tree(x, z, elevval, treeProb, 0);
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
		place_tree(x, z, elevval, treeProb, 0);
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
		place_tree(x, z, elevval, treeProb, 0);
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
		place_tree(x, z, elevval, treeProb, 0);
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 31:
	    // barren land (baseline% sand baseline% stone)
	    if (Math.random() < 0.20) {
		thisblock = blockTypes.Stone;
	    } else {
		place_tree(x, z, elevval, treeProb, -1);
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
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    place_tree(x, z, elevval, treeProb, 2);
	    break;
	case 42:
	    // evergreen forest (grass with tree #2)
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    place_tree(x, z, elevval, treeProb, 1);
	    break;
	case 43:
	    // mixed forest (grass with either tree)
	    if (Math.random() < 0.50) {
		thisblock = 0;
	    } else {
		thisblock = 1;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, blockTypes.Grass);
	    place_tree(x, z, elevval, treeProb, thisblock);
	    break;
	case 51:
	    // dwarf scrub (grass with 25% stone)
	    if (Math.random() < 0.25) {
		thisblock = blockTypes.Stone;
	    } else {
		thisblock = blockTypes.Grass
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
		place_tree(x, z, elevval, treeProb, 1);
	    } else {
		thisblock = blockTypes.Water;
	    }
	    layers(x, z, elevval, blockTypes.Dirt, 1, thisblock);
	    break;
	case 91:
	    // palustrine forested wetlands
	    if (Math.random() < 0.50) {
		thisblock = blockTypes.Grass;
		place_tree(x, z, elevval, treeProb, 0);
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
		place_tree(x, z, elevval, treeProb, 2);
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
    var x = arguments[0];
    var z = arguments[1];
    var elevval = arguments[2];
    var bottom = baseline;
    var top = filler+elevval;

    // examples:
    // layers(x, y, elevval, blockType.Stone);
    //  - fill everything from baseline to elevval with stone
    // layers(x, y, elevval, blockType.Dirt, 2, blockType.Water);
    //  - fill everything from baseline to elevval-2 with dirt, rest with water
    // layers(x, y, elevval, blockType.Stone, 2, blockType.Dirt, 1, blockType.Grass);
    //  - fill everything from baseline to elevval-2 with dirt, one layer with dirt, and top layer with grass
    for (var index = 3; index < arguments.length; index++) {
	// arguments[index] better be a block type
	// FIXME: good people would check this value
	block = arguments[index];
	// if this is the last argument, fill it up to elevval
	if (index == (arguments.length-1)) {
	    map.fillBlocks(x, 1, bottom, top, z, 1, block);
	} else {
	    // next argument better be a number
	    // FIXME: good people would check this value
	    index++;
	    depth = arguments[index];
	    map.fillBlocks(x, 1, bottom, top-depth, z, 1, block);
	    bottom = top - depth;
	}
    }
}

// generates random numbers from min to max (inclusive?)
function random(min, max) {
    return Math.floor(Math.random()*(max-min))+min;
}

// places leaves and tree
function make_tree(x, z, elevval, height, treeType) {
    var treeDate = new Date();
    var startTime = treeDate.getTime();

    print('Placing a tree of type '+treeType+' and height '+height+' at '+x+', '+z+', '+elevval+'...');
    // -1 = cactus, 0 = regular, 1 = redwood, 2 = birch
    var maxleafheight = height+1;
    for (var index = 1; index < maxleafheight; index++) {
	var y = elevval+index;
	if (treeType == -1) {
	    map.setBlock(x, y, z, blockTypes.Cactus);
	    map.setBlock(x, y+1, z, blockTypes.Cactus);
	    map.setBlock(x, y+2, z, blockTypes.Cactus);
	    break;
	}
	if (index > 2) {
	    var curleafwidth;
	    var curleafheight = index-2;
	    var tobottom = curleafheight-2;
	    var totop = maxleafheight-curleafheight;
	    if (tobottom < totop) {
		curleafwidth = tobottom+1;
	    } else {
		curleafwidth = totop+1;
	    }
	    map.fillBlocks(x-curleafwidth, x+curleafwidth, y, 1, z-curleafwidth, z+curleafwidth, blockTypes.Leaves);
	    for (var xindex = x-curleafwidth; xindex < x+curleafwidth+1; xindex++) for (var zindex = z-curleafwidth; zindex < z+curleafwidth+1; zindex++) {
	     	map.setBlockData(xindex, y, zindex, treeType);
	    }
	}
	if (index < height) {
	    map.setBlock(x, y, z, blockTypes.Log);
	    map.setBlockData(x, y, z, treeType);
	}
    }
    treeDate = new Date();
    var endTime = treeDate.getTime();
    var treeDelta = Math.round(endTime - startTime)/1000;
    print('... done! in '+treeDelta+' seconds');
}

function place_tree(x, z, elevval, prob, treeType) {
    var height;
    var chance = Math.random();
    if (chance < prob) {
	print('chance was '+chance);
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
	make_tree(x, z, elevval, height, treeType);
    }
}

// everything an explorer needs, for now
function equip_player() {
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
    print('Land cover statistics ('+lcTotal+' total):');
    var B = [];
    for (var i in lcCount)
	B.push({v: i, c: lcCount[i]});
    B.sort(function (a, b) { return b.c - a.c; });
    for (var element in B) {
	var Bev = B[element].v;
    	if (lcCount[Bev] > 0) {
	    var lcPercent = Math.round((lcCount[Bev]*10000)/lcTotal)/100.0;
	    print('  '+lcCount[Bev]+' ('+lcPercent+'%): '+lcType[Bev]);
    	}
    }
}

function main() {
    var mainDate = new Date();
    var startTime = mainDate.getTime();

    // what are we doing?
    print('Creating world from region '+region);

    // initialize the land cover variables
    populateLandCoverVariables(lcType, lcCount);

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

    printLandCoverStatistics(lcType, lcCount);

    equip_player();

    mainDate = new Date();
    var endTime = mainDate.getTime();
    var mainDelta = Math.round(endTime - startTime)/1000;
    print('Processing done -- took ' + mainDelta + ' seconds.');
}

// hey ho let's go
main();
