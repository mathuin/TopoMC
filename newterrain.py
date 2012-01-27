from random import random

class Terrain():
    """Base class for landcover definitions."""
    # Each landcover class is a subclass of Terrain.

    # corresponds to landcover product ID
    key = 'XXX'
    # key: landcover value
    # value: productID-specific method calling Terrain methods
    # (required default method with key of zero)
    # NB: must be defined *after* productID-specific methods!
    terdict = dict()

    # common Terrain methods
    @staticmethod
    def placedirt(crustval):
        return [crustval, 'Dirt']

    @staticmethod
    def placewater(crustval, bathyval, ice=False):
        newcrustval = int(max(0, crustval-(bathyval/2)))
        return [newcrustval, 'Sand', bathyval-1, 'Water', 1, 'Ice' if ice else 'Water']

    @staticmethod
    def placedeveloped(crustval, stoneProb=0):
        if (random() < stoneProb):
            blockType = 'Stone'
        else:
            blockType = 'Grass'
            # FIXME: add tree probability
        return [crustval, 'Dirt', 1, blockType]

    @staticmethod
    def placedesert(crustval, stoneProb=0):
        if (random() < stoneProb):
            blockType = 'Stone'
        else:
            blockType = 'Sand'
            # FIXME: add cactus probability
            # what about sugar cane?
        return [crustval, 'Sand', 2, blockType]
    
    @staticmethod
    def placeforest(crustval, redwoodProb):
        if (random() < redwoodProb):
            treeType = 'Redwood'
        else:
            treeType = 'Birch'
        # FIXME: add tree probability
        return [crustval, 'Dirt', 1, 'Grass']

    @staticmethod
    def placeshrubland(crustval, stoneProb):
        if (random() < stoneProb):
            blockType = 'Stone'
        else:
            blockType = 'Grass'
            # FIXME: add shrub probability
        return [crustval, 'Dirt', 1, blockType]

    @staticmethod
    def placegrass(crustval):
        return [crustval, 'Dirt', 1, 'Grass']

    # method that actually places terrain
    def place(self, lc, crustval, bathyval):
        if self.key == 'XXX' or self.terdict == {}:
            raise AttributeError, "terrain unpopulated"
        try:
            self.terdict[lc]
        except KeyError:
            print "lc value %s not found!" % lc
        return self.terdict.get(lc, self.terdict[0])(crustval, bathyval)
        

