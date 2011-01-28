// constants
var sealevel = 64;
var baseline = 50; // below here is just stone
var filler = sealevel - baseline;

// set maxMapHeight to a conservative value
var maxMapHeight = 125 - sealevel;

// these are outside the loop
// variables set throughout the run
var elevval = 0;
var maxelev = 0;
var spawnx = 0;
var spawny = 0;
var spawnz = 0;

// tiling constants
var tilerows = 256;
var tilecols = 256;

// what region are we doing?
var region = 'BlockIsland';
// FIXME: these should have defaults to "all files" eventually
var minrows = 0;
var mincols = 0;
var maxrows = 1520;
var maxcols = 1990;

// land cover statistics
var lcType = {};
var lcCount = {};
var lcTotal = 0;

// inside the loop
function processImage(offset_x, offset_z) {
    var imagedir = "Images/"+region;
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
    for (var x = 0; x < size_x; x++) {
	for (var z = 0; z < size_z; z++) {
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
	    processLcval(lcval, real_x, real_z, elevval)
	}
    }

    // print out status
    var imageDate = new Date();
    var endTime = imageDate.getTime();
    var imageDelta = Math.round(endTime - startTime)/1000;
    print('... finished in ' + imageDelta + ' seconds.')
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
	99 : "Estuarine Aquatic Bed",
    };
    for (var i in lcMetaType) {
	lcType[i] = lcMetaType[i];
	lcCount[i] = 0;
    }
}

// process a given land cover value
function processLcval(lcval, x, z, elevval) {
    lcTotal++;
    if (!(lcval in lcType)) {
	print('unexpected value for land cover: ' + lcval);
	lcCount[0]++;
	one_layer(x, z, elevval, blockTypes.Dirt);
    } else {
	lcCount[lcval]++;
	switch(lcval) {
	case 11:
	    // water 2m over sand
	    // IDEA: survey neighboring squares
	    // if at least one is not water, use 1m, not 2m
	    two_layer(x, z, elevval, 2, blockTypes.Sand, blockTypes.Water);
	    break;
	case 12:
	    // ice
	    // FIXME: how to put ice on?
	    two_layer(x, z, elevval, 2, blockTypes.Sand, blockTypes.Water);
	    break;
	case 21:
	    // developed/open-space (20% stone 80% grass rand tree)
	    one_layer_rand(x, z, elevval, 0.2, blockTypes.Stone, blockTypes.Dirt);
	    break;
	case 22:
	    // developed/open-space (35% stone 65% grass rand tree)
	    one_layer_rand(x, z, elevval, 0.35, blockTypes.Stone, blockTypes.Dirt);
	    break;
	case 23:
	    // developed/open-space (65% stone 35% grass rand tree)
	    one_layer_rand(x, z, elevval, 0.65, blockTypes.Stone, blockTypes.Dirt);
	    break;
	case 24:
	    // developed/open-space (90% stone 10% grass rand tree)
	    one_layer_rand(x, z, elevval, 0.90, blockTypes.Stone, blockTypes.Dirt);
	    break;
	case 31:
	    // barren land (baseline% sand baseline% stone)
	    one_layer(x, z, elevval, blockTypes.Sand);
	    break;
	case 32:
	    // unconsolidated shore (sand)
	    one_layer(x, z, elevval, blockTypes.Sand);
	    break;
	case 41:
	    // deciduous forest (grass with tree #1)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 42:
	    // evergreen forest (grass with tree #2)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 43:
	    // mixed forest (grass with either tree)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 51:
	    // dwarf scrub (grass with 25% stone)
	    // FIXME: how to put grass on dirt?
	    one_layer_rand(x, z, elevval, 0.25, blockTypes.Stone, blockTypes.Dirt);
	    break;
	case 52:
	    // shrub/scrub (grass with 25% stone)
	    // FIXME: how to put grass on dirt?
	    one_layer_rand(x, z, elevval, 0.25, blockTypes.Stone, blockTypes.Dirt);
	    break;
	case 71:
	    // grasslands/herbaceous
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 72:
	    // sedge/herbaceous
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 73:
	    // lichens (90% stone 10% grass)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, 0.10, blockTypes.dirt, blockTypes.Stone);
	    break;
	case 74:
	    // moss (90% stone 10% grass)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, 0.10, blockTypes.dirt, blockTypes.Stone);
	    break;
	case 81:
	    // pasture/hay
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 82:
	    // cultivated crops
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 90:
	    // woody wetlands (grass with rand trees and -1m water)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 91:
	    // palustrine forested wetlands (grass with rand trees and -1m water)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 92:
	    // palustrine scrub/shrub wetlands (grass with baseline% -1m water)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 93:
	    // estuarine forested wetlands (grass with rand trees and water)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 94:
	    // estuarine scrub/shrub wetlands (grass with baseline% -1m water)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 95:
	    // emergent herbaceous wetlands (grass with baseline% -1m water)
	    // FIXME: how to put grass on dirt?
	    one_layer(x, z, elevval, blockTypes.Dirt);
	    break;
	case 96:
	    // palustrine emergent wetlands-persistent (-1m water?)
	    two_layer(x, z, elevval, 1, blockTypes.Dirt, blockTypes.Water);
	    break;
	case 97:
	    // estuarine emergent wetlands (-1m water)
	    two_layer(x, z, elevval, 1, blockTypes.Dirt, blockTypes.Water);
	    break;
	case 98:
	    // palustrine aquatic bed (-1m water)
	    two_layer(x, z, elevval, 1, blockTypes.Dirt, blockTypes.Water);
	    break;
	case 99:
	    // estuarine aquatic bed (-1m water)
	    two_layer(x, z, elevval, 1, blockTypes.Dirt, blockTypes.Water);
	    break;
	}
    }
}

// fills a column with a single block type 
function one_layer(x, z, elevval, blockType) {
    map.fillBlocks(x, 1, baseline, filler+elevval, z, 1, blockType);
}

// fills a column with a base block type then covers it with a block type
function two_layer(x, z, elevval, depth, baseblockType, topblockType) {
    var underlayer = elevval-depth;
    map.fillBlocks(x, 1, baseline, filler+underlayer, z, 1, baseblockType);
    map.fillBlocks(x, 1, sealevel+underlayer, depth, z, 1, topblockType);
}

// fills a column with this or that depending
function one_layer_rand(x, z, elevval, prob, lowerblock, upperblock) {
    var thisblock;
    if (Math.random() < prob) {
	thisblock = lowerblock; 
    } else {
	thisblock = upperblock;
    }
    one_layer(x, z, elevval, thisblock);
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
    B = [];
    for (i in lcCount)
	B.push({v: i, c: lcCount[i]});
    B.sort(function (a, b) { return b.c - a.c });
    for (element in B) {
	i = B[element].v;
    	if (lcCount[i] > 0) {
	    lcPercent = Math.round((lcCount[i]*10000)/lcTotal)/100.0;
	    print('  '+lcCount[i]+' ('+lcPercent+'%): '+lcType[i]);
    	}
    }
}

function main() {
    print('Begin TopoMC demo');
    var mainDate = new Date();
    var startTime = mainDate.getTime();

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

    var mainDate = new Date();
    var endTime = mainDate.getTime();
    var mainDelta = Math.round(endTime - startTime)/1000;
    print('Processing done -- took ' + mainDelta + ' seconds.');
    print('End TopoMC Demo');
}

// hey ho let's go
main()
