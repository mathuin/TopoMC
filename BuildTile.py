#!/usr/bin/env python

# pseudo multiprocessing nonsense

import logging
logging.basicConfig(level=logging.WARNING)
from tile import Tile

import sys
import os
import yaml

def main(argv):
    """Takes region name and tile coordinates, and builds a world."""
    # zero is command
    name = argv[1]
    tilex = argv[2]
    tiley = argv[3]
    
    # build the region
    yamlfile = file(os.path.join('Regions', name, 'Region.yaml'))
    myRegion = yaml.load(yamlfile)
    yamlfile.close()

    # build the tile
    myTile = Tile(myRegion, tilex, tiley)
    myTile.build()
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))
