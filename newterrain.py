from random import random, choice
from newutils import materialNamed
import os
import sys
sys.path.append('..')
from pymclevel import mclevel, schematic
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
                  'L06': { 52: 51, 72: 71, 73: 71, 74: 71, 90: 91, 95: 91 },
                  'L92': { 85: 21, 21: 22, 22: 24, 23: 25, 32: 31, 62: 82, 83: 82, 84: 82, 92: 90 } }

    # local constants
    tallgrassProb = 0.05

    # tree constants
    # move to newtree.py
    treeProb = 0.001
    forestProb = 0.03

    # structure methods
    @staticmethod
    def newstructure(layout, offset):
        # NB: error checking needed
        retval = dict()
        retval['layout'] = layout
        retval['offset'] = offset
        # do speed testing
        retval['width'] = len(layout)
        retval['length'] = len(layout[0])
        retval['height'] = Terrain.depth(layout[0][0])
        Terrain.checkstructure(retval)
        return retval

    @staticmethod
    def compressrow(yrow):
        """Compresses duplicate values in rows."""
        retval = []
        for elem in yrow:
            if retval and retval[-1][1] == elem[1]:
                retval[-1] = ((retval[-1][0] + elem[0]), elem[1])
            else:
                retval.append(elem)
        return retval

    @staticmethod
    def importstructure(tag, offset=2):
        if tag==None:
            raise AttributeError, "tag required"
        filename = '%s.schematic' % tag
        schem = mclevel.fromFile(filename)
        layout = [[Terrain.compressrow([(1, (int(schem.Blocks[elemX, elemZ, elemY]), int(schem.Data[elemX, elemZ, elemY]))) for elemY in xrange(schem.Height)]) for elemZ in xrange(schem.Length)] for elemX in xrange(schem.Width)]
        return Terrain.newstructure(layout, offset)

    @staticmethod
    def checkstructure(structure, verbose=False):
        if not all([len(row) == structure['length'] for row in structure['layout']]):
            raise AttributeError, "not all rows are the same width"

        if not all([Terrain.depth(col) == structure['height'] for row in structure['layout'] for col in row]):
            raise AttributeError, "not all cols are the same height"

        if verbose:
            print "structure has dimensions %dX x %dY x %dZ" % (structure['length'], structure['height'], structure['width'])

    @staticmethod
    def placestructure(structure, x, y, z, crustval):
        return (y + structure['height'] - structure['offset'], 
                [(crustval, 'Dirt')] + structure['layout'][x % structure['length']][z % structure['width']],
                None)
        
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
    def placedevelopedsimple(x, y, z, crustval, stoneProb=0):
        # possibly place tall grass?
        (blockType, tree) = ('Stone', None) if random() < stoneProb else ('Grass', Terrain.placetree(Terrain.treeProb, 'Regular'))
        return (y, [(crustval, 'Dirt'), (1, blockType)], tree)

    @staticmethod
    def placeopenspace(x, y, z, crustval, stoneProb=0):
        try:
            Terrain.openspacestructure
        except AttributeError:
            if os.path.exists('Labyrinth.schematic'):
                Terrain.openspacestructure = Terrain.importstructure('Labyrinth')
            else:
                # temporary placeholder
                # when multiple structures for developed are placed
                # random layouts with appropriate coverage will be built
                Terrain.openspacestructure = Terrain.newstructure(layout=[[[(1, 'Stone')]]], offset=0)
        return Terrain.placestructure(Terrain.openspacestructure, x, y, z, crustval)

    @staticmethod
    def placelowintensity(x, y, z, crustval, stoneProb=0):
        try:
            Terrain.lowintensitystructure
        except AttributeError:
            if os.path.exists('Neighborhood.schematic'):
                Terrain.lowintensitystructure = Terrain.importstructure('Neighborhood')
            else:
                # temporary placeholder
                # when multiple structures for developed are placed
                # random layouts with appropriate coverage will be built
                Terrain.lowintensitystructure = Terrain.newstructure(layout=[[[(1, 'Stone')]]], offset=0)
        return Terrain.placestructure(Terrain.lowintensitystructure, x, y, z, crustval)

    @staticmethod
    def placemedintensity(x, y, z, crustval, stoneProb=0):
        try:
            Terrain.medintensitystructure
        except AttributeError:
            if os.path.exists('Apartments.schematic'):
                Terrain.medintensitystructure = Terrain.importstructure('Apartments')
            else:
                # temporary placeholder
                # when multiple structures for developed are placed
                # random layouts with appropriate coverage will be built
                Terrain.medintensitystructure = Terrain.newstructure(layout=[[[(1, 'Stone')]]], offset=0)
        return Terrain.placestructure(Terrain.medintensitystructure, x, y, z, crustval)

    @staticmethod
    def placehighintensity(x, y, z, crustval, stoneProb=0):
        try:
            Terrain.highintensitystructure
        except AttributeError:
            if os.path.exists('Apartments.schematic'):
                Terrain.highintensitystructure = Terrain.importstructure('Apartments')
            else:
                # temporary placeholder
                # when multiple structures for developed are placed
                # random layouts with appropriate coverage will be built
                Terrain.highintensitystructure = Terrain.newstructure(layout=[[[(1, 'Stone')]]], offset=0)
        return Terrain.placestructure(Terrain.highintensitystructure, x, y, z, crustval)

    @staticmethod
    def placecommercial(x, y, z, crustval, stoneProb=0):
        try:
            Terrain.commercialstructure
        except AttributeError:
            if os.path.exists('Commercial.schematic'):
                Terrain.commercialstructure = Terrain.importstructure('Commercial')
            else:
                # temporary placeholder
                # when multiple structures for developed are placed
                # random layouts with appropriate coverage will be built
                Terrain.commercialstructure = Terrain.newstructure(layout=[[[(1, 'Stone')]]], offset=0)
        return Terrain.placestructure(Terrain.commercialstructure, x, y, z, crustval)

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

    @staticmethod
    def placecrops(x, y, z, crustval):
        try:
            Terrain.cropsstructure
        except AttributeError:
            if os.path.exists('crops.schematic'):
                Terrain.cropsstructure = Terrain.importstructure('crops')
            else:
                # a very simple substitute
                Terrain.cropsstructure = Terrain.newstructure(layout=[[[(1, 'Farmland'), (1, ('Crops', 7))]]], offset=1)
        return Terrain.placestructure(Terrain.cropsstructure, x, y, z, crustval)

    @staticmethod
    def placefarm(x, y, z, crustval):
        try:
            Terrain.farmstructure
        except AttributeError:
            if os.path.exists('Farm.schematic'):
                Terrain.farmstructure = Terrain.importstructure('Farm')
            else:
                # a very simple substitute
                Terrain.cropsstructure = Terrain.newstructure(layout=[[[(1, 'Farmland'), (1, ('Crops', 7))]]], offset=1)
        return Terrain.placestructure(Terrain.farmstructure, x, y, z, crustval)

    @staticmethod
    def depth(column):
        """Calculate the depth of the column."""
        # NB: confirm that the column matches expectation
        if type(column[0]) is tuple:
            pairs = column
        else:
            print "oops, missed one!"
            pairs = zip(column[::2], column[1::2])
        retval = sum([pair[0] for pair in pairs])
        return retval

    # valid terrain functions
    # 0: default
    def zero(x, y, z, crustval, bathyval):
        return (y, [(crustval, 'Obsidian')], None)

    # 11: water
    def eleven(x, y, z, crustval, bathyval):
        return Terrain.placewater(x, y, z, crustval, bathyval)

    # 12: ice
    def twelve(x, y, z, crustval, bathyval):
        return Terrain.placeice(x, y, z, crustval)

    # 21: developed/open-space (<20% developed)
    def twentyone(x, y, z, crustval, bathyval):
        return Terrain.placeopenspace(x, y, z, crustval, stoneProb=0.1)

    # 22: developed/low-intensity (20-49% developed)
    def twentytwo(x, y, z, crustval, bathyval):
        return Terrain.placelowintensity(x, y, z, crustval, stoneProb=0.35)

    # 23: developed/medium-intensity (50-79% developed)
    def twentythree(x, y, z, crustval, bathyval):
        return Terrain.placemedintensity(x, y, z, crustval, stoneProb=0.65)

    # 24: developed/high-intensity (80-100% developed)
    def twentyfour(x, y, z, crustval, bathyval):
        return Terrain.placehighintensity(x, y, z, crustval, stoneProb=0.9)

    # 25: commercial-industrial-transportation
    def twentyfive(x, y, z, crustval, bathyval):
        return Terrain.placecommercial(x, y, z, crustval, stoneProb=1)

    # 31: barren land (rock/sand/clay)
    def thirtyone(x, y, z, crustval, bathyval):
        return Terrain.placedesert(x, y, z, crustval, stoneProb=0.50)

    # 32: transitional
    def thirtytwo(x, y, z, crustval, bathyval):
        return Terrain.placedesert(x, y, z, crustval)

    # 41: deciduous forest
    def fortyone(x, y, z, crustval, bathyval):
        return Terrain.placeforest(x, y, z, crustval, 'Redwood')

    # 42: evergreen forest
    def fortytwo(x, y, z, crustval, bathyval):
        return Terrain.placeforest(x, y, z, crustval, 'Birch')

    # 43: mixed forest
    def fortythree(x, y, z, crustval, bathyval):
        return Terrain.placeforest(x, y, z, crustval, ['Redwood', 'Birch'])

    # 51: shrubland
    def fiftyone(x, y, z, crustval, bathyval):
        return Terrain.placeshrubland(x, y, z, crustval, stoneProb=0.25)

    # 71: grassland
    def seventyone(x, y, z, crustval, bathyval):
        return Terrain.placegrass(x, y, z, crustval, tallgrassProb=0.75)

    # 81: pasture/hay
    def eightyone(x, y, z, crustval, bathyval):
        return Terrain.placegrass(x, y, z, crustval, tallgrassProb=0.50)

    # 82: crops
    def eightytwo(x, y, z, crustval, bathyval):
        return Terrain.placefarm(x, y, z, crustval)

    # 91: wetlands
    def ninetyone(x, y, z, crustval, bathyval):
        return Terrain.placegrass(x, y, z, crustval)

    # dictionary used by place
    terdict = { 0: zero, 11: eleven, 12: twelve, 21: twentyone, 22: twentytwo, 23: twentythree, 24: twentyfour, 25: twentyfive, 31: thirtyone, 32: thirtytwo, 41: fortyone, 42: fortytwo, 43: fortythree, 51: fiftyone, 71: seventyone, 81: eightyone, 82: eightytwo, 91: ninetyone }

    # method that actually places terrain
    @staticmethod
    def place(x, y, z, lcval, crustval, bathyval):
        try:
            Terrain.terdict[lcval]
        except KeyError:
            print "lcval value %s not found!" % lcval
        (y, column, tree) = Terrain.terdict.get(lcval, Terrain.terdict[0])(x, y, z, crustval, bathyval)
        merged = [ (depth, (block, 0)) if type(block) is not tuple else (depth, block) for (depth, block) in column ]
        blocks = []
        datas = []
        overstone = Terrain.depth(merged)
        core = [ (1, ('Bedrock', 0)), (y-overstone-1, ('End Stone', 0)) ] + merged
        base = 0
        while core:
            (depth, (block, data)) = core.pop(0)
            [ blocks.append((y, materialNamed(block) if type(block) is str else block)) for y in xrange(base, base+depth) ]
            [ datas.append((y, data)) for y in xrange(base, base+depth) ]
            base += depth
        return blocks, datas, tree


