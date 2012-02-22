#!/usr/bin/env python

import logging
logging.basicConfig(level=logging.WARNING)
from newregion import Region
import sys
import argparse
import os
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def main(argv):
    """Rebuilds maps on broken regions."""
    parser = argparse.ArgumentParser(description='Prepares downloaded regions for building.')
    parser.add_argument('--name', required=True, type=str, help='name of region')

    args = parser.parse_args()

    print "Preparing region %s..." % args.name
    yamlfile = file(os.path.join('Regions', args.name, 'Region.yaml'))
    myRegion = yaml.load(yamlfile)
    yamlfile.close()

    myRegion.buildmap()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
