# structure module
from newutils import height
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
        self.height = height(self.layout[0][0])

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

        if not all([height(col) == self.height for row in self.layout for col in row]):
            raise AttributeError, "not all cols are the same height"

        if verbose:
            print "structure has dimensions %dX x %dY x %dZ" % (self.length, self.height, self.width)

    @staticmethod
    def use(key, name, nameoffset, layout, offset):
        def decorator(target):
            def wrapper(*args, **kwargs):
                # major assumption: 
                # args are (x, y, z, crustval, bathyval, doStructures)
                x = args[0]
                y = args[1]
                z = args[2]
                crustval = args[3]
                bathyval = args[4]
                doStructures = args[5]
                try:
                    Structure.structs[key]
                except KeyError:
                    if doStructures:
                        try:
                            newstruct = Structure(tag=name, offset=nameoffset)
                        except IOError:
                            newstruct = Structure(layout=layout, offset=offset)
                    else:
                        newstruct = Structure(layout=layout, offset=offset)
                    Structure.structs[key] = newstruct
                struct = Structure.structs[key]
                return (y + struct.height - struct.offset, [(crustval, 'Dirt')] + struct.layout[x % struct.length][z % struct.width], None)
            return wrapper
        return decorator
