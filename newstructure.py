# structure module
import os
import sys
sys.path.append('..')
from pymclevel import mclevel

class Structure:
    """This class is for maintaining structures.  

    Structures are MCEdit schematics which are associated with landcover types.  
    When the landcover type comes up, the relevant portion of the structure is placed.

    Structures should be designed to mesh well together.  The sample structures all
    come from a specific pattern so streets and sidewalks go well together, but do 
    not be limited by this example!"""

    # dict
    # key: landcover value
    # value: structure object
    structs = dict()

    # sigh -- cut and pasted from Terrain.
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

    def __init__(self, tag=None, layout=None, offset=1):
        # handles:
        # - file-based (tag=foo, layout=None)
        # - layout-based (tag=None, layout=[[[(1, 'Stone')]]])
        if tag == None and layout == None:
            raise AttributeError, 'tag or layout must be specified'
        if layout == None:
            filename = '%s.schematic' % tag
            if not os.path.exists(filename):
                raise IOError, 'no file found'
            else:
                schem = mclevel.fromFile(filename)
                self.layout = [[Structure.compressrow([(1, (int(schem.Blocks[elemX, elemZ, elemY]), int(schem.Data[elemX, elemZ, elemY]))) for elemY in xrange(schem.Height)]) for elemZ in xrange(schem.Length)] for elemX in xrange(schem.Width)]
        else:
            self.layout = layout
        self.offset = offset
        self.width = len(self.layout)
        self.length = len(self.layout[0])
        self.height = Structure.depth(self.layout[0][0])

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

    def check(self, verbose=False):
        if not all([len(row) == self.length for row in self.layout]):
            raise AttributeError, "not all rows are the same width"

        if not all([Structure.depth(col) == self.height for row in self.layout for col in row]):
            raise AttributeError, "not all cols are the same height"

        if verbose:
            print "structure has dimensions %dX x %dY x %dZ" % (self.length, self.height, self.width)

    @staticmethod
    def use(key, name, nameoffset, layout, offset):
        def decorator(target):
            def wrapper(*args, **kwargs):
                try:
                    Structure.structs[key]
                except KeyError:
                    try:
                        newstruct = Structure(tag=name, offset=nameoffset)
                    except IOError:
                        newstruct = Structure(layout=layout, offset=offset)
                    Structure.structs[key] = newstruct
                struct = Structure.structs[key]
                # below we make the HUGE ASSUMPTION
                # that *args starts with (x, y, z, crustval)
                x = args[0]
                y = args[1]
                z = args[2]
                crustval = args[3]
                return (y + struct.height - struct.offset, [(crustval, 'Dirt')] + struct.layout[x % struct.length][z % struct.width], None)
            return wrapper
        return decorator
