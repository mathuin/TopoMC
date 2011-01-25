print('Begin RealMC demo');

// Load an image object
var lcimg = JCraft.Components.Images.Load("lcimage.gif");
var elevimg = JCraft.Components.Images.Load("elevimage.gif");

var latrange = lcimg.height;
var longrange = lcimg.width;

var sealevel = 64;
var baseline = 50; // below here is just stone
var filler = sealevel - baseline;

// set maxMapHeight to a conservative value
var maxMapHeight = 125 - sealevel;

map.fillBlocks(0, latrange, 0, baseline, 0, longrange, blockTypes.Stone);

//fill bottom and sides with bedrock
map.fillBlocks(0, latrange, 0, 1, 0, longrange, blockTypes.Bedrock);

map.fillBlocks(0, latrange, 0, sealevel+1, 0, 1, blockTypes.Bedrock);
map.fillBlocks(0, latrange, 0, sealevel+1, longrange, 1, blockTypes.Bedrock);
map.fillBlocks(0, 1, 0, sealevel+1, 0, longrange, blockTypes.Bedrock);
map.fillBlocks(latrange, 1, 0, sealevel+1, 0, longrange, blockTypes.Bedrock);

var lcval = 0;
var elevval = 0;
var maxelev = 0;
var spawnx = 0;
var spawny = 0;
var spawnz = 0;

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

for (x = 0; x < latrange; x++) {
    for (z = 0; z < longrange; z++) {
	// flipping it backwards because Z increases west not east
	flatindex = (x * longrange) + (longrange - z - 1);
	lcval = lcimg[flatindex];
	elevval = elevimg[flatindex];
	if (elevval > maxMapHeight) {
	    print('oh no elevation ' + elevval + ' is too high');
	    elevval = maxMapHeight;
	}
	if (elevval > maxelev) {
	    maxelev = elevval;
	    spawnx = x;
	    spawnz = z;
	    spawny = sealevel+elevval;
	}
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
}

// set player position and spawn point (in this case, equal)
print('Setting spawn values: ' + spawnx + ', ' + spawny + ', ' + spawnz);
map.spawn = { x: spawnx, y: spawny+2, z: spawnz };
map.playerLocation = map.spawn;

map.playerInventory.Add(new Item(itemTypes.IronSword));
map.playerInventory.Add(new Item(itemTypes.IronPickaxe));
map.playerInventory.Add(new Item(itemTypes.IronShovel));
map.playerInventory.Add(new Item(itemTypes.IronAxe));
map.playerInventory.AddAt(new Item(blockTypes.Torch), 8);
var sandstack = new Item(blockTypes.Sand);
sandstack.Count = 64;
map.playerInventory.AddAt(sandstack, 7);

print('End RealMC Demo');
