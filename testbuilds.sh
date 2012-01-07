#!/bin/sh

# testbuilds.sh - 2011Feb06 - mathuin@gmail.com

# This script tests the build process so I can make sure 
# that changes do not break things.

# The script now records profiling data for later analysis.

# This script requires c10t to render a map of the world.
# c10t can be found at git://github.com/udoprog/c10t.git

: ${DATASET:="BlockIsland"}
: ${ARRAYDIR:="Arrays/$DATASET"}
: ${WORLDDIR:="Worlds/$DATASET"}
: ${PROFDATESTR:=$(date +"%Y%m%d%H%m")}
: ${PROFBAFILE:="BA-$PROFDATESTR.prof"}
: ${PROFBWFILE:="BW-$PROFDATESTR.prof"}
: ${BAOPTS:="--scale 15"}
: ${BWOPTS:=""}
: ${IMAGE:="$DATASET.png"}
: ${MAPPER:="../c10t/build/c10t"}
: ${MAPPEROPTS:="-z -w $WORLDDIR -o $IMAGE"}

rm -rf $ARRAYDIR $WORLDDIR $IMAGE && \
time python -m cProfile -o $PROFBAFILE ./BuildArrays.py --region $DATASET --processes 1 $BAOPTS && \
time python -m cProfile -o $PROFBWFILE ./BuildWorld.py --region $DATASET --processes 1 $BWOPTS && \
$MAPPER $MAPPEROPTS && \
display $IMAGE 
