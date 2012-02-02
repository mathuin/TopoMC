from random import random, choice
#from newtree import placeTree, treeProb, forestProb

class Terrain():
    """Base class for landcover definitions."""
    # Each landcover class is a subclass of Terrain.

    # local constants
    tallgrassProb = 0.05

    # tree constants
    # move to newtree.py
    treeProb = 0.001
    forestProb = 0.03
    # add a list of valid trees here

    # corresponds to landcover product ID
    key = 'XXX'
    # key: landcover value
    # value: productID-specific method calling Terrain methods
    # (required default method with key of zero)
    # NB: must be defined *after* productID-specific methods!
    terdict = dict()

    # helper methods
    @staticmethod
    def placetree(treeProb, whichTree):
        # two possibilities for whichTree:
        # string: 100% this kind of tree
        # list: equal chances on which kind of tree
        treeType = choice(whichTree) if type(whichTree) is list else whichTree
        return treeType if random() < treeProb else None

    # common Terrain methods
    # all Terrain methods accept (x, y, z, crustval) at least
    # all Terrain methods return (y, column, tree)
    # y: integer level for top of the column (usually unmodified)
    # column: list of counts and blocks with optional data
    # tree: either a type of tree or None
    @staticmethod
    def placedirt(x, y, z, crustval):
        return (y, [crustval, 'Dirt'], None)

    @staticmethod
    def placewater(x, y, z, crustval, bathyval, ice=False):
        newcrustval = int(max(0, crustval-(bathyval/2)))
        return (y, [newcrustval, 'Sand', bathyval-1, 'Water', 1, 'Ice' if ice else 'Water'], None)

    @staticmethod
    def placedeveloped(x, y, z, crustval, stoneProb=0):
        # possibly place tall grass?
        (blockType, tree) = ('Stone', None) if random() < stoneProb else ('Grass', Terrain.placetree(Terrain.treeProb, 'Regular'))
        return (y, [crustval, 'Dirt', 1, blockType], tree)

    @staticmethod
    def placedesert(x, y, z, crustval, stoneProb=0):
        choices = ['Cactus', 'Cactus', 'Cactus', 'Sugar Cane']
        (blockType, tree) = ('Stone', None) if random() < stoneProb else ('Sand', Terrain.placetree(Terrain.treeProb, choices))
        return (y, [crustval, 'Sand', 2, blockType], tree)
    
    @staticmethod
    def placeforest(x, y, z, crustval, trees):
        tree = Terrain.placetree(Terrain.forestProb, trees)
        return (y, [crustval, 'Dirt', 1, 'Grass'], tree)

    @staticmethod
    def placeshrubland(x, y, z, crustval, stoneProb):
        (blockType, tree) = ('Stone', None) if random() < stoneProb else ('Grass', Terrain.placetree(Terrain.treeProb, 'Shrub'))
        return (y, [crustval, 'Dirt', 1, blockType], tree)

    @staticmethod
    def placegrass(x, y, z, crustval, tallgrassProb=0.05):
        if (random() < tallgrassProb):
            # 80% Tall Grass, 10% Flower, 10% Rose
            choices = [('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1), 'Flower', 'Rose']
            return (y+1, [crustval, 'Dirt', 1, 'Grass', 1, choice(choices)], None)
        else:
            return (y, [crustval, 'Dirt', 1, 'Grass'], None)

    @staticmethod
    def placecrops(x, y, z, crustval):
        # a repeating pattern
        # two rows of wheat, a row of water, two rows of wheat, a road, 
        # two rows for melons, a row of water, two rows for pumpkins, a road
        # with crossroads every ten blocks
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

        return (y+1, column, None)

    # method that actually places terrain
    def place(self, x, y, z, lcval, crustval, bathyval):
        if self.key == 'XXX' or self.terdict == {}:
            raise AttributeError, "terrain unpopulated"
        try:
            self.terdict[lcval]
        except KeyError:
            print "lcval value %s not found!" % lcval
        (y, column, tree) = self.terdict.get(lcval, self.terdict[0])(x, y, z, crustval, bathyval)
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
        return blocks, datas, tree


