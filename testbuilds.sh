#!/bin/sh

# testbuilds.sh - 2011Feb06 - mathuin@gmail.com

# This script tests the build process so I can make sure 
# that changes do not break things.

# The script now records profiling data for later analysis.

# This script requires c10t to render a map of the world.
# c10t can be found at git://github.com/udoprog/c10t.git

: ${REGION:="BlockIsland"}
: ${IMAGEDIR:="Images/$REGION"}
: ${PROFDATESTR:=$(date +"%Y%m%d%H%m")}
: ${PROFBIFILE:="BI-$PROFDATESTR.prof"}
: ${PROFBWFILE:="BW-$PROFDATESTR.prof"}
: ${BIOPTS:="--scale 15"}
: ${WORLDDIR:="Worlds/$REGION"}
: ${BWOPTS:=""}
: ${IMAGE:="$REGION.png"}
: ${MAPPER:="../c10t/build/c10t"}
: ${MAPPEROPTS:="-z -w $WORLDDIR -o $IMAGE"}

rm -rf $IMAGEDIR $WORLDDIR $IMAGE && \
python -m cProfile -o $PROFBIFILE ./BuildImages.py --region $REGION --processes 1 $BIOPTS && \
python -m cProfile -o $PROFBWFILE ./BuildWorld.py --region $REGION --processes 1 $BWOPTS && \
$MAPPER $MAPPEROPTS && \
display $IMAGE 
