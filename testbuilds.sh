#!/bin/sh

# testbuilds.sh - 2011Feb06 - mathuin@gmail.com

# This script tests the build process so I can make sure 
# that changes do not break things.

# The script now records profiling data for later analysis.

# This script requires c10t to render a map of the world.
# c10t can be found at git://github.com/udoprog/c10t.git

: ${DATASET:="BlockIsland"}
: ${DATADIR:="Images/$DATASET"}
: ${PROFDATESTR:=$(date +"%Y%m%d%H%m")}
: ${PROFBIFILE:="BI-$PROFDATESTR.prof"}
: ${PROFBWFILE:="BW-$PROFDATESTR.prof"}
: ${BIOPTS:="--scale 15"}
: ${WORLDNAME:="TestWorld"}
: ${BWOPTS:="--world $WORLDNAME"}
: ${IMAGE:="$WORLDNAME.png"}
: ${MAPPER:="../c10t/build/c10t"}
: ${MAPPEROPTS:="-z -w $WORLDNAME -o $IMAGE"}

rm -rf $DATADIR $WORLDNAME $IMAGE && \
python -m cProfile -o $PROFBIFILE ./BuildImages.py --region $DATASET --processes 1 $BIOPTS && \
python -m cProfile -o $PROFBWFILE ./BuildWorld.py --region $DATASET --processes 1 $BWOPTS && \
$MAPPER $MAPPEROPTS && \
display $IMAGE 
