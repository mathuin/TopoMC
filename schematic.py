# schematic module
from utils import height
import os
import sys
sys.path.append('..')
from pymclevel import mclevel

class Schematic:
    """Schematics are associated with landcover types.  When the
    landcover type comes up, the relevant portion of the schematic is
    placed.

    Schematics should be designed to mesh well together.  The sample schematics all
    come from a specific pattern so streets and sidewalks go well together, but do 
    not be limited by this example!"""
    # dict
    # key: landcover value
    # value: schematic object
    schems = dict()

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
                self.layout = [[Schematic.compressrow([(1, (int(schem.Blocks[elemX, elemZ, elemY]), int(schem.Data[elemX, elemZ, elemY]))) for elemY in xrange(schem.Height)]) for elemZ in xrange(schem.Length)] for elemX in xrange(schem.Width)]
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
            print "schematic has dimensions %dX x %dY x %dZ" % (self.length, self.height, self.width)

    @staticmethod
    def use(key, name, nameoffset, layout, offset):
        def decorator(target):
            def wrapper(*args, **kwargs):
                # major assumption: 
                # args are (x, y, z, crustval, bathyval, doSchematics)
                x = args[0]
                y = args[1]
                z = args[2]
                crustval = args[3]
                bathyval = args[4]
                doSchematics = args[5]
                try:
                    Schematic.schems[key]
                except KeyError:
                    if doSchematics:
                        try:
                            newschem = Schematic(tag=name, offset=nameoffset)
                        except IOError:
                            newschem = Schematic(layout=layout, offset=offset)
                    else:
                        newschem = Schematic(layout=layout, offset=offset)
                    Schematic.schems[key] = newschem
                schem = Schematic.schems[key]
                return (y + schem.height - schem.offset, [(crustval, 'Dirt')] + schem.layout[x % schem.length][z % schem.width], None)
            return wrapper
        return decorator
