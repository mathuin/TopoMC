#!/bin/bash

# warpelev.sh - 2011Jan24 - mathuin@gmail.com

# This script warps the elevation file for a particular region
# to match the land cover file.

# example:  ./warpelev.sh BlockIsland

while [ -n "$*" ]; do
    region=$1
    shift
    # find files
    lctiff=`find ./Datasets/${region}/[0-9]*/ -name "[0-9]*.tif" -print`
    if [ 'x${lctiff}' = 'x' ]; then
	echo Landcover TIF not found!
	exit
    fi
    elevtiff=`find ./Datasets/${region}/NED_[0-9]*/ -name "NED_[0-9]*.tif" -print`
    if [ 'x${elevtiff}' = 'x' ]; then
	echo Elevation TIF not found!
	exit
    fi
    elevorig=${elevtiff}-orig
    elevnew=${elevtiff}-new

    # back up original elevation tiff
    if [ ! -f ${elevorig} ]; then
	cp ${elevtiff} ${elevorig}
    fi

    # populate PRF with SRS
    gdalinfo ${lctiff} | sed -e "1,/Coordinate System is:/d" -e "/Origin =/,\$d" | xargs echo > /tmp/crazy.prf

    # now warp the elevation tiff
    gdalwarp -t_srs /tmp/crazy.prf ${elevorig} ${elevnew} && mv ${elevnew} ${elevtiff}
done