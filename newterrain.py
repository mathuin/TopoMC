from random import random, choice
from newutils import materialNamed, height
from newschematic import Schematic
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

class Terrain:
    """Base class for landcover definitions."""

    # terrain translation
    # key = productID
    # value = dict(key=old, value=new)
    translate = { 'L01': { 32: 31, 52: 51, 72: 71, 73: 71, 74: 71, 90: 91, 92: 91, 93: 91, 94: 91, 95: 91, 96: 91, 97: 91, 98: 91, 99: 91 },
                  'L04': { 32: 31, 52: 51, 72: 71, 73: 71, 74: 71, 90: 91, 92: 91, 93: 91, 94: 91, 95: 91, 96: 91, 97: 91, 98: 91, 99: 91 },
                  'L07': { 32: 31, 52: 51, 72: 71, 73: 71, 74: 71, 90: 91, 92: 91, 93: 91, 94: 91, 95: 91, 96: 91, 97: 91, 98: 91, 99: 91 },
                  'L10': { 32: 31, 52: 51, 72: 71, 73: 71, 74: 71, 90: 91, 92: 91, 93: 91, 94: 91, 95: 91, 96: 91, 97: 91, 98: 91, 99: 91 },
                  'L06': { 52: 51, 72: 71, 73: 71, 74: 71, 90: 91, 95: 91 },
                  'L92': { 85: 21, 21: 22, 22: 24, 23: 25, 32: 31, 62: 82, 83: 82, 84: 82, 92: 90 } }

    # local constants
    tallgrassProb = 0.05

    # tree constants
    # move to newtree.py
    treeProb = 0.001
    forestProb = 0.03

    # schematic defaults
    # 21: 10%, 22: 35%, 23: 65%, 24: 90%, 25: 95%
    layout21 = [[[(1, 'Stone' if random() < 0.1 else 'Grass')] for x in xrange(10)] for x in xrange(10)]
    layout22 = [[[(1, 'Stone' if random() < 0.35 else 'Grass')] for x in xrange(10)] for x in xrange(10)]
    layout23 = [[[(1, 'Stone' if random() < 0.65 else 'Grass')] for x in xrange(10)] for x in xrange(10)]
    layout24 = [[[(1, 'Stone' if random() < 0.90 else 'Grass')] for x in xrange(10)] for x in xrange(10)]
    layout25 = [[[(1, 'Stone' if random() < 0.95 else 'Grass')] for x in xrange(10)] for x in xrange(10)]

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
        return (y, [(crustval, 'Dirt')], None)

    @staticmethod
    def placewater(x, y, z, crustval, bathyval):
        # NB: no longer valid for 12!
        newcrustval = int(max(0, crustval-(bathyval/2)))
        return (y, [(newcrustval, 'Sand'), (bathyval, 'Water')], None)

    @staticmethod
    def placeice(x, y, z, crustval):
        return (y+1, [(crustval, 'Dirt'), (1, 'Snow Layer')], None)

    @staticmethod
    def placedesert(x, y, z, crustval, stoneProb=0):
        choices = ['Cactus', 'Cactus', 'Cactus', 'Sugar Cane']
        (blockType, tree) = ('Stone', None) if random() < stoneProb else ('Sand', Terrain.placetree(Terrain.treeProb, choices))
        return (y, [(crustval, 'Sand'), (2, blockType)], tree)
    
    @staticmethod
    def placeforest(x, y, z, crustval, trees):
        return (y, [(crustval, 'Dirt'), (1, 'Grass')], Terrain.placetree(Terrain.forestProb, trees))

    @staticmethod
    def placeshrubland(x, y, z, crustval, stoneProb):
        (blockType, tree) = ('Stone', None) if random() < stoneProb else ('Grass', Terrain.placetree(Terrain.treeProb, 'Shrub'))
        return (y, [(crustval, 'Dirt'), (1, blockType)], tree)

    @staticmethod
    def placegrass(x, y, z, crustval, tallgrassProb=0.05):
        if (random() < tallgrassProb):
            # 80% Tall Grass, 10% Flower, 10% Rose
            choices = [('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1),  ('Tall Grass', 1), 'Flower', 'Rose']
            return (y+1, [(crustval, 'Dirt'), (1, 'Grass'), (1, choice(choices))], None)
        else:
            return (y, [(crustval, 'Dirt'), (1, 'Grass')], None)

    # valid terrain functions
    # 0: default
    def zero(x, y, z, crustval, bathyval, doSchematics):
        return (y, [(crustval, 'Obsidian')], None)

    # 11: water
    def eleven(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placewater(x, y, z, crustval, bathyval)

    # 12: ice
    def twelve(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placeice(x, y, z, crustval)

    # 21: developed/open-space (<20% developed)
    #@Schematic.use(21, 'OpenSpace', 2, [[[(1, 'Stone')]]], 0)
    @Schematic.use(21, 'OpenSpace', 2, layout21, 0)
    def twentyone(x, y, z, crustval, bathyval, doSchematics):
        pass

    # 22: developed/low-intensity (20-49% developed)
    @Schematic.use(22, 'Neighborhood', 2, layout22, 0)
    def twentytwo(x, y, z, crustval, bathyval, doSchematics):
        pass

    # 23: developed/medium-intensity (50-79% developed)
    @Schematic.use(23, 'School', 2, layout23, 0)
    def twentythree(x, y, z, crustval, bathyval, doSchematics):
        pass

    # 24: developed/high-intensity (80-100% developed)
    @Schematic.use(24, 'Apartments', 2, layout24, 0)
    def twentyfour(x, y, z, crustval, bathyval, doSchematics):
        pass

    # 25: commercial-industrial-transportation
    @Schematic.use(25, 'Commercial', 2, layout25, 0)
    def twentyfive(x, y, z, crustval, bathyval, doSchematics):
        pass

    # 31: barren land (rock/sand/clay)
    def thirtyone(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placedesert(x, y, z, crustval, stoneProb=0.50)

    # 32: transitional
    def thirtytwo(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placedesert(x, y, z, crustval)

    # 41: deciduous forest
    def fortyone(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placeforest(x, y, z, crustval, 'Redwood')

    # 42: evergreen forest
    def fortytwo(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placeforest(x, y, z, crustval, 'Birch')

    # 43: mixed forest
    def fortythree(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placeforest(x, y, z, crustval, ['Redwood', 'Birch'])

    # 51: shrubland
    def fiftyone(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placeshrubland(x, y, z, crustval, stoneProb=0.25)

    # 71: grassland
    def seventyone(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placegrass(x, y, z, crustval, tallgrassProb=0.75)

    # 81: pasture/hay
    def eightyone(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placegrass(x, y, z, crustval, tallgrassProb=0.50)

    # 82: crops
    @Schematic.use(82, 'Farm', 2, [[[(1, ('Farmland', 7)), (1, ('Crops', 7))]]], 1)
    def eightytwo(x, y, z, crustval, bathyval, doSchematics):
        pass

    # 91: wetlands
    def ninetyone(x, y, z, crustval, bathyval, doSchematics):
        return Terrain.placegrass(x, y, z, crustval)

    # dictionary used by place
    terdict = { 0: zero, 11: eleven, 12: twelve, 21: twentyone, 22: twentytwo, 23: twentythree, 24: twentyfour, 25: twentyfive, 31: thirtyone, 32: thirtytwo, 41: fortyone, 42: fortytwo, 43: fortythree, 51: fiftyone, 71: seventyone, 81: eightyone, 82: eightytwo, 91: ninetyone }

    # method that actually places terrain
    @staticmethod
    def place(x, y, z, lcval, crustval, bathyval, doSchematics):
        try:
            Terrain.terdict[lcval]
        except KeyError:
            print "lcval value %s not found!" % lcval
        (y, column, tree) = Terrain.terdict.get(lcval, Terrain.terdict[0])(x, y, z, crustval, bathyval, doSchematics)
        merged = [ (depth, (block, 0)) if type(block) is not tuple else (depth, block) for (depth, block) in column ]
        blocks = []
        datas = []
        overstone = height(merged)
        core = [ (1, ('Bedrock', 0)), (y-overstone-1, ('End Stone', 0)) ] + merged
        base = 0
        while core:
            (depth, (block, data)) = core.pop(0)
            [ blocks.append((y, materialNamed(block) if type(block) is str else block)) for y in xrange(base, base+depth) ]
            [ datas.append((y, data)) for y in xrange(base, base+depth) ]
            base += depth
        return blocks, datas, tree


