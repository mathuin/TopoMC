# tile class

# REALLY NEED TO SEPARATE OUT THAT WSDL CRAZINESS INTO ANOTHER CLASS

# ./BuildRegion.py does all of this, then generates one big world from all the littles
# in the Tiles/XxY directories and stores it in Region/<name>/World, setting spawn to 
# the first highest altitude plus two Y.

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
