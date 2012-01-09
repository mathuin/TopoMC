# tile class

# tons o notes

# okay, so newregion.py has a class Region that actually works.  
# It'll pull the BlockIsland region, which is startlingly larger than expected.  Eeek.
# what is needed now is to implement all of buildarrays inside a tile class.

# Regions.yaml has enough information in *theory* to generate tiles.

# REALLY NEED TO SEPARATE OUT THAT WSDL CRAZINESS INTO ANOTHER CLASS

# Tiles are in Regions.  I don't think that means a subclass.  
# I think it's more that __init__ needs to refer to a Region and an X/Y pair.
# If the X/Y pair is in the range for the Region (easily checked) the Tile is then
# created.

# What tiles do
# - create a Tiles/XxY directory
# - generate two 288x288 arrays (landcover and elevation)
# - generate a 256x256 array for faux bathymetry
# - generate a 256x256 array for crust values (use constant if you're lazy)
# - generate two 256x256x128 arrays (blocks and data)
# - populate blocks and data with terrain (no trees or ore or building)
# - write Tile.yaml with relevant data (peak at least)
# - build a Minecraft world via pymclevel from blocks and data
# - write that world to disk in Tiles/XxY/World

# ./BuildRegion.py does all of this, then generates one big world from all the littles
# in the Tiles/XxY directories and stores it in Region/<name>/World, setting spawn to 
# the first highest altitude plus two Y.

# But that has to wait for the Tile stuff to work.

class Tile:
    """Tiles are the base render object.  or something."""
    def __init__(self, region, tilex, tiley):
        """Create a tile based on the region and the tile's coordinates."""
        # NB: smart people check that files have been gotten.
        # today we assume that's already been done.

        if (tilex < region.txmin) || (tilex >= region.txmax):
            raise AttributeError, "tilex (%d) must be between %d and %d" % tilex
        if (tiley < region.tymin) || (tiley >= region.tymax):
            raise AttributeError, "tiley (%d) must be between %d and %d" % tiley

        # create the tile directory if necessary
        tiledir = os.path.join('Regions', region.name, 'Tiles', '%dx%d' % (tilex, tiley))
        self.worlddir = os.path.join(tiledir, 'World')
        if os.path.isdir(tiledir):
            shutil.rmtree(tiledir)
        if not os.path.exists(tiledir):
            os.makedirs(self.worlddir)
        else:
            raise IOError, '%s already exists' % tilesdir

        # array for landcover and elevation needs maxdepth-sized borders
        mapsize = region.tilesize + 2 * region.maxdepth

        # generate two mapsize*mapsize arrays for landcover and elevation

        # generate one tilesize*tilesize array for bathymetry

        # generate one tilesize*tilesize array for crust values

        # generate two tilesize*height*tilesize arrays for blocks and data

        # do the terrain thing (no trees, ore or building)

        # write Tile.yaml with relevant data (peak at least)

        # build a Minecraft world via pymclevel from blocks and data

        # write that world to the Tiles/XxY/World directory





if __name__ == '__main__':
    checkTile();
