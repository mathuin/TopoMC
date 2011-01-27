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
var maxrows = 304*5;
var maxcols = 398*5;

// inside the loop
function process_image(offset_x, offset_z) {
    var lcimg = JCraft.Components.Images.Load("Images/"+region+"-lc-"+offset_x+"-"+offset_z+".gif");
    var elevimg = JCraft.Components.Images.Load("Images/"+region+"-elev-"+offset_x+"-"+offset_z+".gif");
    var size_x = lcimg.width;
    var size_z = lcimg.height;
    var stop_x = offset_x+size_x;
    var stop_z = offset_z+size_z;

    // debug output
    print('Image: (' + size_x + ', ' + size_z + ')');
    print('Offset: (' + offset_x + ', ' + offset_z + ')');
    print('Stop: (' + stop_x + ', ' + stop_z + ')');

    // fill bottom of this particular range with bedrock
    map.fillBlocks(offset_x, stop_x, 0, 1, offset_z, stop_z, blockTypes.Bedrock);

    // fill middle chunk of this particular range with stone
    map.fillBlocks(offset_x, stop_x, 1, baseline, offset_z, stop_z, blockTypes.Stone);

    // iterate over the image
    for (x = 0; x < size_x; x++) {
	for (z = 0; z < size_z; z++) {
	    flatindex = (z * size_x) + x;
	    lcval = lcimg[flatindex];
	    elevval = elevimg[flatindex];
	    real_x = offset_x + x;
	    real_z = offset_z + z;
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
	    process_lcval(lcval, real_x, real_z, elevval);
	}
    }
}

// process a given land cover value
function process_lcval(lcval, x, z,elevval) {
    switch(lcval) {
    case 11:
	// water 3m over sand
	two_layer(x, z, elevval, 3, blockTypes.Sand, blockTypes.Water);
	break;
    case 12:
	// ice
	// FIXME: how to put ice on?
	two_layer(x, z, elevval, 3, blockTypes.Sand, blockTypes.Water);
	break;
    case 21:
	// developed/open-space (20% stone 80% grass rand tree)
    case 22:
	// developed/open-space (35% stone 65% grass rand tree)
    case 23:
	// developed/open-space (65% stone 35% grass rand tree)
    case 24:
	// developed/open-space (90% stone 10% grass rand tree)
	one_layer(x, z, elevval, blockTypes.Stone);
	break;
    case 31:
	// barren land (baseline% sand baseline% stone)
    case 32:
	// unconsolidated shore (sand)
	one_layer(x, z, elevval, blockTypes.Sand);
	break;
    case 41:
	// deciduous forest (grass with tree #1)
    case 42:
	// evergreen forest (grass with tree #2)
    case 43:
	// evergreen forest (grass with either tree)
	// FIXME: how to put grass on dirt?
	one_layer(x, z, elevval, blockTypes.Dirt);
	break;
    case 51:
	// dwarf scrub (grass with 25% stone)
    case 52:
	// shrub/scrub (grass with 25% stone)
	// FIXME: how to put grass on dirt?
	one_layer(x, z, elevval, blockTypes.Dirt);
	break;
    case 71:
	// grasslands/herbaceous
    case 72:
	// sedge/herbaceous
	// FIXME: how to put grass on dirt?
	one_layer(x, z, elevval, blockTypes.Dirt);
	break;
    case 73:
	// lichens (90% stone 10% grass)
    case 74:
	// moss (90% stone 10% grass)
	one_layer(x, z, elevval, blockTypes.Stone);
	break;
    case 81:
	// pasture/hay
    case 82:
	// cultivated crops
	// FIXME: how to put grass on dirt?
	one_layer(x, z, elevval, blockTypes.Dirt);
	break;
    case 90:
	// woody wetlands (grass with rand trees and -2m water)
    case 91:
	// palustrine forested wetlands (grass with rand trees and -2m water)
    case 92:
	// palustrine scrub/shrub wetlands (grass with baseline% -2m water)
    case 93:
	// estuarine forested wetlands (grass with rand trees and water)
    case 94:
	// estuarine scrub/shrub wetlands (grass with baseline% -2m water)
    case 95:
	// emergent herbaceous wetlands (grass with baseline% -2m water)
	one_layer(x, z, elevval, blockTypes.Dirt);
	break;
    case 96:
	// palustrine emergent wetlands-persistent (-2m water?)
    case 97:
	// estuarine emergent wetlands (-2m water)
    case 98:
	// palustrine aquatic bed (-2m water)
    case 99:
	// estuarine aquatic bed (-2m water)
	two_layer(x, z, elevval, 2, blockTypes.Dirt, blockTypes.Water)
	    break;
    default:
	print('unexpected value for land cover: ' + lcval);
	one_layer(x, z, elevval, blockTypes.Dirt);
	break;
    }
}

// fills a column with a base block type then covers it with a block type
function two_layer(x, z, elevval, depth, baseblockType, topblockType) {
    underlayer = elevval-depth;
    map.fillBlocks(x, 1, baseline, filler+underlayer, z, 1, baseblockType);
    map.fillBlocks(x, 1, sealevel+underlayer, depth, z, 1, topblockType);
}

// fills a column with a single block type 
function one_layer(x, z, elevval, blockType) {
    map.fillBlocks(x, 1, baseline, filler+elevval, z, 1, blockType);
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

function main() {
    print('Begin TopoMC demo');

    // for loop time!
    for (row = 0; row < maxrows; row += tilerows) {
	for (col = 0; col < maxcols; col += tilecols) {
	    process_image(row, col);
	}
    }

    // maximum elevation
    print('Maximum elevation: ' + maxelev);

    // set player position and spawn point (in this case, equal)
    print('Setting spawn values: ' + spawnx + ', ' + spawny + ', ' + spawnz);
    map.spawn = { x: spawnx, y: spawny+2, z: spawnz };
    map.playerLocation = map.spawn;

    equip_player();

    print('End TopoMC Demo');
}

// hey ho let's go
main()
