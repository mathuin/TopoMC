from random import random
#from newtree import placeTree, treeProb, forestProb

class Terrain():
    """Base class for landcover definitions."""
    # Each landcover class is a subclass of Terrain.

    # local constants
    tallgrassProb = 0.05

    # corresponds to landcover product ID
    key = 'XXX'
    # key: landcover value
    # value: productID-specific method calling Terrain methods
    # (required default method with key of zero)
    # NB: must be defined *after* productID-specific methods!
    terdict = dict()

    # common Terrain methods
    @staticmethod
    def placedirt(x, y, z, crustval):
        return (y, [crustval, 'Dirt'])

    @staticmethod
    def placewater(x, y, z, crustval, bathyval, ice=False):
        newcrustval = int(max(0, crustval-(bathyval/2)))
        return (y, [newcrustval, 'Sand', bathyval-1, 'Water', 1, 'Ice' if ice else 'Water'])

    @staticmethod
    def placedeveloped(x, y, z, crustval, stoneProb=0):
        if (random() < stoneProb):
            blockType = 'Stone'
        else:
            blockType = 'Grass'
            #placeTree(x, z, y, treeProb, 'Regular')
            # FIXME: add tall grass probability
        return (y, [crustval, 'Dirt', 1, blockType])

    @staticmethod
    def placedesert(x, y, z, crustval, stoneProb=0):
        if (random() < stoneProb):
            blockType = 'Stone'
        else:
            blockType = 'Sand'
            #placeTree(x, z, y, treeProb, 'Cactus')
            # what about sugar cane?
        return (y, [crustval, 'Sand', 2, blockType])
    
    @staticmethod
    def placeforest(x, y, z, crustval, redwoodProb):
        if (random() < redwoodProb):
            treeType = 'Redwood'
        else:
            treeType = 'Birch'
        #placeTree(x, z, y, forestProb, treeType)
        return (y, [crustval, 'Dirt', 1, 'Grass'])

    @staticmethod
    def placeshrubland(x, y, z, crustval, stoneProb):
        if (random() < stoneProb):
            blockType = 'Stone'
        else:
            blockType = 'Grass'
            #placeTree(x, z, y, treeProb, 'Shrub')
        return (y, [crustval, 'Dirt', 1, blockType])

    @staticmethod
    def placegrass(x, y, z, crustval, tallgrassProb=0.05):
        if (random() < tallgrassProb):
            topping = random()
            if (topping < 0.80):
                capblock = ('Tall Grass', 1)
            elif (topping < 0.90):
                capblock = 'Flower'
            else:
                capblock = 'Rose'
            return (y+1, [crustval, 'Dirt', 1, 'Grass', 1, capblock])
        else:
            return (y, [crustval, 'Dirt', 1, 'Grass'])

    @staticmethod
    def placecrops(x, y, z, crustval):
        # for now always crops, possibly add in sugar cane
        # to be "proper" it should be done in groups
        # Okay, new crops approach: repeating patterns.
        # level y:
        # 0 1 2 3 4 5 0 1 2 3 4 5
        # f f w f f c f f w f f c
        # except every 10 when it is:
        # c c w c c c c c w c c c
        # level y+1:
        # W W a W W a a M a P a a
        # except every 10 when it is:
        # a s c S a a a s c S a a
        # key:
        # f = farmland
        # w = water
        # c = cobblestone
        # W = wheat (full height)
        # M = melon (full height)
        # P = pumpkin (full height)
        # a = air
        # s = cobble stair facing right
        # S = cobble stair facing left
        farm = [
            [1, 'Farmland', 1, ('Crops', 7)], 
            [1, 'Farmland', 1, ('Crops', 7)], 
            [1, 'Water', 1, 'Air'], 
            [1, 'Farmland', 1, ('Crops', 7)], 
            [1, 'Farmland', 1, ('Crops', 7)], 
            [1, 'Cobblestone', 1, 'Air'],
            [1, 'Farmland', 1, 'Air'],
            [1, 'Farmland', 1, ('Melon Stem', 7)],
            [1, 'Water', 1, 'Air'],
            [1, 'Farmland', 1, ('Pumpkin Stem', 7)],
            [1, 'Farmland', 1, 'Air'],
            [1, 'Cobblestone', 1, 'Air'] ]
        path = [
            [1, 'Cobblestone', 1, 'Air'],
            [1, 'Cobblestone', 1, ('Stone Stairs', 1)], 
            [1, 'Water', 1, 'Cobblestone' ],
            [1, 'Cobblestone', 1, ('Stone Stairs', 3)], 
            [1, 'Cobblestone', 1, 'Air'],
            [1, 'Cobblestone', 1, 'Air'],
            [1, 'Cobblestone', 1, 'Air'],
            [1, 'Cobblestone', 1, ('Stone Stairs', 1)], 
            [1, 'Water', 1, 'Cobblestone' ],
            [1, 'Cobblestone', 1, ('Stone Stairs', 3)], 
            [1, 'Cobblestone', 1, 'Air'],
            [1, 'Cobblestone', 1, 'Air'] ]

        if len(farm) != len(path):
            raise AttributeError, "farm and path lists not the same length"
        else:
            farmwidth = len(farm)
        layout = path if z % 10 == 0 else farm
        column = [crustval, 'Dirt'] + layout[x % farmwidth]

        return (y+1, column)

    # method that actually places terrain
    def place(self, x, y, z, lcval, crustval, bathyval):
        if self.key == 'XXX' or self.terdict == {}:
            raise AttributeError, "terrain unpopulated"
        try:
            self.terdict[lcval]
        except KeyError:
            print "lcval value %s not found!" % lcval
        (y, column) = self.terdict.get(lcval, self.terdict[0])(x, y, z, crustval, bathyval)
        # now 
        merged = [ (x, 0) if type(x) is str else x for x in column ]
        blocks = []
        datas = []
        top = y
        overstone = sum([merged[elem] for elem in xrange(len(merged)) if elem % 2 == 0])
        merged.insert(0, ('Bedrock', 0))
        merged.insert(1, top-overstone-1)
        merged.insert(2, ('Stone', 0))
        while (len(merged) > 0 or top > 0):
            # better be a block
            (block, data) = merged.pop()
            if (len(merged) > 0):
                layer = merged.pop()
            else:
                layer = top
            # now do something
            if (layer > 0):
                # NB: there's gotta be a way to not need the y, bah
                [blocks.append((y, block)) for y in xrange(top-layer,top)]
                [datas.append((y, data)) for y in xrange(top-layer,top)]
                top -= layer
        return blocks, datas


