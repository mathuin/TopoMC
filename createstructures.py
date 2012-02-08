# create structures for Terrain module

from newterrain import Terrain

# farmland

def createcrops():
    # Two rows, farm and path.  One path every nine rows of farm.
    farm = [
        [(1, 'Farmland'), (1, ('Crops', 7))], 
        [(1, 'Farmland'), (1, ('Crops', 7))], 
        [(1, 'Water'), (1, 'Air')], 
        [(1, 'Farmland'), (1, ('Crops', 7))], 
        [(1, 'Farmland'), (1, ('Crops', 7))], 
        [(1, 'Cobblestone'), (1, 'Air')],
        [(1, 'Farmland'), (1, 'Air')],
        [(1, 'Farmland'), (1, ('Melon Stem', 7))],
        [(1, 'Water'), (1, 'Air')],
        [(1, 'Farmland'), (1, ('Pumpkin Stem', 7))],
        [(1, 'Farmland'), (1, 'Air')],
        [(1, 'Cobblestone'), (1, 'Air')] ]
    path = [
        [(1, 'Cobblestone'), (1, 'Air')],
        [(1, 'Cobblestone'), (1, 'Stone Stairs')],
        [(1, 'Water'), (1, 'Cobblestone')],
        [(1, 'Cobblestone'), (1, ('Stone Stairs', 1))], 
        [(1, 'Cobblestone'), (1, 'Air')],
        [(1, 'Cobblestone'), (1, 'Air')],
        [(1, 'Cobblestone'), (1, 'Air')],
        [(1, 'Cobblestone'), (1, 'Stone Stairs')], 
        [(1, 'Water'), (1, 'Cobblestone')],
        [(1, 'Cobblestone'), (1, ('Stone Stairs', 1))], 
        [(1, 'Cobblestone'), (1, 'Air')],
        [(1, 'Cobblestone'), (1, 'Air')] ]
    layout = [farm, farm, farm, farm, farm, farm, farm, farm, farm, path]
    offset = 1
    newcrops = Terrain.newstructure(layout, offset)
    Terrain.checkstructure(newcrops, verbose=True)
    Terrain.savestructure(newcrops, 'crops')

def createdeveloped():
    # Simple building
    air = [(1, 'Stone'), (5, 'Air')]
    corner = [(6, 'Stone')]
    wall = [(3, 'Stone'), (2, 'Glass'), (1, 'Stone')]
    middle = [(1, 'Stone'), (4, 'Air'), (1, 'Stone')]
    opening = [(1, 'Stone'), (2, 'Air'), (3, 'Stone')]
    layout = [
        [air, air, air, air, air, air, air],
        [air, corner, wall, wall, wall, corner, air],
        [air, wall, middle, middle, middle, wall, air],
        [air, wall, middle, middle, middle, wall, air],
        [air, wall, middle, middle, middle, wall, air],
        [air, wall, middle, middle, middle, wall, air],
        [air, corner, wall, opening, wall, corner, air],
        [air, air, air, air, air, air, air]
        ]
    offset=1
    developed = Terrain.newstructure(layout, offset)
    Terrain.checkstructure(developed, verbose=True)
    Terrain.savestructure(developed, 'developed')

def createstructures():
    createcrops()
    createdeveloped()

if __name__ == '__main__':
    createstructures()
    
