// constants
var sealevel = 64;
var baseline = 32; // below here is just stone
var filler = sealevel - baseline;

// set maxMapHeight to a conservative value
var maxMapHeight = 125 - sealevel;

// these are outside the loop
// processImage modifies these as it runs
var maxelev = 0;
var maxbathy = 0;
var spawnx = 0;
var spawny = sealevel;
var spawnz = 0;

// what region are we doing?
var region = 'BlockIsland';
var imagedir = "Images/"+region;
// FIXME: these should have defaults to "all files" eventually
var minrows = 0;
var mincols = 0;
var maxrows = 1520;
var maxcols = 1990;
//var maxrows = 2167;
//var maxcols = 2140;
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
    var bathyimg = JCraft.Components.Images.Load(imagedir+"/bathy-"+offset_x+"-"+offset_z+".gif");
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
	var bathyval = bathyimg[flatindex];
	var real_x = offset_x + x;
	var real_z = offset_z + z;
	if (elevval > maxMapHeight) {
	    print('oh no elevation ' + elevval + ' is too high');
	    elevval = maxMapHeight;
	}
	if (elevval > maxelev) {
	    maxbathy = elevval;
	    spawnx = real_x;
	    spawnz = real_z;
	    spawny = elevval;
	}
	if (bathyval > maxbathy) {
	    maxelev = bathyval;
	}
	processLcval(lcval, real_x, real_z, elevval, bathyval);
    }
	
    // print out status
    imageDate = new Date();
    var endTime = imageDate.getTime();
    var imageDelta = Math.round(endTime - startTime)/1000;
    print('... finished in ' + imageDelta + ' seconds.');
}

function populateLandCoverVariables(lcType, lcCount, treeType, treeCount) {
    // first add all the text values for land covers
    // http://www.mrlc.gov/nlcd_definitions.php
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
function processLcval(lcval, x, z, elevval, bathyval) {
    var thisblock; // scratch space
    lcTotal++;
    if (!(lcval in lcType)) {
	print('unexpected value for land cover: ' + lcval);
	lcCount[0]++;
	layers(x, z, elevval, blockTypes.Dirt);
    } else {
	lcCount[lcval]++;
	// http://www.mrlc.gov/nlcd_definitions.php
	switch(lcval) {
	case 11:
	    // water
	    layers(x, z, elevval, blockTypes.Sand, bathyval, blockTypes.Water);
	    break;
	case 12:
	    // ice
	    layers(x, z, elevval, blockTypes.Sand, bathyval, blockTypes.Ice);
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
    // layers(x, y, elevval, blockTypes.Stone);
    //  - fill everything from baseline to elevval with stone
    // layers(x, y, elevval, blockTypes.Dirt, 2, blockTypes.Water);
    //  - elevval down two levels of water, rest dirt
    // layers(x, y, elevval, blockTypes.Stone, 1, blockTypes.Dirt, 1, blockTypes.Grass);
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
	if (slice > 0) {
	    map.fillBlocks(x, 1, top-slice, slice, z, 1, block);
	    top -= slice;
	}
    } while (data.length > 0 || bottom < top);
}

// generates random numbers from min to max (inclusive?)
function random(min, max) {
    return Math.floor(Math.random()*(max-min))+min;
}

// places leaves and tree
function makeTree(x, z, elevval, height, type) {
    var maxleafheight = height+1;
    var trunkheight = 1;
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
		    var deltax = Math.abs(xindex-x);
		    var deltaz = Math.abs(zindex-z);
		    var sumsquares = Math.pow(deltax,2)+Math.pow(deltaz,2);
		    if (Math.sqrt(sumsquares) < curleafwidth*.75) {
			map.setBlock(xindex, y, zindex, blockTypes.Leaves);
	     		map.setBlockData(xindex, y, zindex, type);
		    }
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
    var dirtstack = new Item(blockTypes.Dirt);
    dirtstack.Count = 64;
    map.playerInventory.AddAt(dirtstack, 7);
    var torchstack = new Item(blockTypes.Torch);
    torchstack.count = 64;
    map.playerInventory.AddAt(torchstack, 8);
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

// This building is made of stone and glass, and has an wooden door.
// It also has some torches on the corners and over the door.
// The center of the building is the (x, elevval, z) point.
// The dimensions of the walls are length (x), width (y), and height (z)
function building(x, z, elevval, length, width, height, side) {
    var x_offset = Math.floor(length/2);
    var right = x-x_offset;
    var left = x+x_offset;
    var z_offset = Math.floor(width/2);
    var back = z-z_offset;
    var front = z+z_offset;
    var bottom = sealevel+elevval-1;
    var top = bottom+height;
    var doorx;
    var doorz;
    var doorleftx;
    var doorleftz;
    var doorrightx;
    var doorrightz;
    var doorhinge;
    var doortorchx;
    var doortorchz;
    var doortorchdata;
    var stairholex1;
    var stairholez1;
    var stairholex2;
    var stairholez2;
    var stairholex3;
    var stairholez3;
    var stairholex4;
    var stairholez4;
    var stairdata;
    switch(side) {
    case 0:
    default:
	// facing forward
	doorx = x;
	doorz = front;
	doorleftx = x-1;
	doorleftz = front;
	doorrightx = x+1;
	doorrightz = front;
	doorhinge = 0x2;
	doortorchx = x;
	doortorchz = front+1;
	doortorchdata = 0x3;
	stairholex1 = right+1;
	stairholez1 = back+4;
	stairholex2 = right+1;
	stairholez2 = back+3;
	stairholex3 = right+1;
	stairholez3 = back+2;
	stairholex4 = right+1;
	stairholez4 = back+1;
	stairdata = 0x3;
	break;
    case 1:
	// facing left
	doorx = left;
	doorz = z;
	doorleftx = left;
	doorleftz = z-1;
	doorrightx = left;
	doorrightz = z+1;
	doorhinge = 0x3;
	doortorchx = left+1;
	doortorchz = z;
	doortorchdata = 0x1;
	stairholex1 = right+4;
	stairholez1 = front-1;
	stairholex2 = right+3;
	stairholez2 = front-1;
	stairholex3 = right+2;
	stairholez3 = front-1;
	stairholex4 = right+1;
	stairholez4 = front-1;
	stairdata = 0x1;
	break;
    case 2:
	// facing backward
	doorx = x;
	doorz = back;
	doorleftx = x+1;
	doorleftz = back;
	doorrightx = x-1;
	doorrightz = back;
	doorhinge = 0x0;
	doortorchx = x;
	doortorchz = back-1;
	doortorchdata = 0x4;
	stairholex1 = left-1;
	stairholez1 = front-4;
	stairholex2 = left-1;
	stairholez2 = front-3;
	stairholex3 = left-1;
	stairholez3 = front-2;
	stairholex4 = left-1;
	stairholez4 = front-1;
	stairdata = 0x2;
	break;
    case 3:
	// right
	doorx = right;
	doorz = z;
	doorleftx = right;
	doorleftz = z+1;
	doorrightx = right;
	doorrightz = z-1;
	doorhinge = 0x1;
	doortorchx = right-1;
	doortorchz = z;
	doortorchdata = 0x2;
	stairholex1 = left-4;
	stairholez1 = back+1;
	stairholex2 = left-3;
	stairholez2 = back+1;
	stairholex3 = left-2;
	stairholez3 = back+1;
	stairholex4 = left-1;
	stairholez4 = back+1;
	stairdata = 0x0;
	break;
    }

    // clear out all the existing space
    map.fillBlocks(right, length, bottom, height, back, width, blockTypes.Air);
    // floor
    map.fillBlocks(right, length, bottom, 1, back, width, blockTypes.Stone);
    // back wall
    map.fillBlocks(right, length, bottom, height, back, 1, blockTypes.Stone);
    map.fillBlocks(right+1, length-2, bottom+2, height-2, back, 1, blockTypes.Glass);
    // right wall
    map.fillBlocks(right, 1, bottom, height, back, width, blockTypes.Stone);
    map.fillBlocks(right, 1, bottom+2, height-2, back+1, width-2, blockTypes.Glass);
    // left wall
    map.fillBlocks(left, 1, bottom, height, back, width, blockTypes.Stone);
    map.fillBlocks(left, 1, bottom+2, height-2, back+1, width-2, blockTypes.Glass);
    // front wall
    map.fillBlocks(right, length, bottom, height, front, 1, blockTypes.Stone);
    map.fillBlocks(right+1, length-2, bottom+2, height-2, front, 1, blockTypes.Glass);
    // roof
    map.fillBlocks(right, length, top, 1, back, width, blockTypes.Stone);
    map.fillBlocks(right+1, length-2, top, 1, back+1, width-2, blockTypes.Glass);
    // now about that door
    map.setBlock(doorleftx, bottom+3, doorleftz, blockTypes.Stone);
    map.setBlock(doorleftx, bottom+2, doorleftz, blockTypes.Stone);
    map.setBlock(doorleftx, bottom+1, doorleftz, blockTypes.Stone);
    map.setBlock(doorx, bottom+3, doorz, blockTypes.Stone);
    map.setBlock(doorx, bottom+2, doorz, blockTypes.WoodenDoor);
    map.setBlock(doorx, bottom+1, doorz, blockTypes.WoodenDoor);
    map.setBlockData(doorx, bottom+2, doorz, doorhinge | 0x8);
    map.setBlockData(doorx, bottom+1, doorz, doorhinge);
    map.setBlock(doorrightx, bottom+3, doorrightz, blockTypes.Stone);
    map.setBlock(doorrightx, bottom+2, doorrightz, blockTypes.Stone);
    map.setBlock(doorrightx, bottom+1, doorrightz, blockTypes.Stone);

    // stories!
    for (var level = bottom+4; level<(top-3); level+=4) {
	map.fillBlocks(right, length, level, 1, back, width, blockTypes.Stone);
     	map.setBlock(stairholex1, level, stairholez1, blockTypes.Air);
     	map.setBlock(stairholex2, level, stairholez2, blockTypes.Air);
     	map.setBlock(stairholex3, level, stairholez3, blockTypes.Air);
     	map.setBlock(stairholex4, level, stairholez4, blockTypes.StoneStairs);
      	map.setBlock(stairholex3, level-1, stairholez3, blockTypes.StoneStairs);
     	map.setBlock(stairholex2, level-2, stairholez2, blockTypes.StoneStairs);
     	map.setBlock(stairholex1, level-3, stairholez1, blockTypes.StoneStairs);
 	map.setBlockData(stairholex4, level, stairholez4, stairdata);
	map.setBlockData(stairholex3, level-1, stairholez3, stairdata);
 	map.setBlockData(stairholex2, level-2, stairholez2, stairdata);
 	map.setBlockData(stairholex1, level-3, stairholez1, stairdata);
    }

    // torches
    // on the back wall
    map.setBlock(right, top, back-1, blockTypes.Torch);
    map.setBlockData(right, top, back-1, 0x4);
    map.setBlock(left, top, back-1, blockTypes.Torch);
    map.setBlockData(left, top, back-1, 0x4);
    // on the side walls
    map.setBlock(right-1, top, back, blockTypes.Torch);
    map.setBlockData(right-1, top, back, 0x2);
    map.setBlock(left+1, top, back, blockTypes.Torch);
    map.setBlockData(left+1, top, back, 0x1);
    map.setBlock(right-1, top, front, blockTypes.Torch);
    map.setBlockData(right-1, top, front, 0x2);
    map.setBlock(left+1, top, front, blockTypes.Torch);
    map.setBlockData(left+1, top, front, 0x1);
    // on the front wall
    map.setBlock(right, top, front+1, blockTypes.Torch);
    map.setBlockData(right, top, front+1, 0x3);
    map.setBlock(left, top, front+1, blockTypes.Torch);
    map.setBlockData(left, top, front+1, 0x3);
    // over the door
    map.setBlock(doortorchx, bottom+3, doortorchz, blockTypes.Torch);
    map.setBlockData(doortorchx, bottom+3, doortorchz, doortorchdata);
    // on the roof
    map.setBlock(right, top+1, back, blockTypes.Torch);
    map.setBlockData(right, top+1, back, 0x5);
    map.setBlock(left, top+1, back, blockTypes.Torch);
    map.setBlockData(left-1, top+1, back, 0x5);
    map.setBlock(right, top+1, front, blockTypes.Torch);
    map.setBlockData(right, top+1, front, 0x5);
    map.setBlock(left, top+1, front, blockTypes.Torch);
    map.setBlockData(left, top+1, front, 0x5);
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
    print('Maximum depth: ' + maxbathy);

    // have a building!
    building(spawnx, spawnz, spawny, 9, 7, 8, 0);

    // set player position and spawn point (in this case, equal)
    print('Setting spawn values: ' + spawnx + ', ' + (sealevel+spawny+2) + ', ' + spawnz);
    map.spawn = { x: spawnx, y: sealevel+spawny+2, z: spawnz };
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
