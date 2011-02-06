#!/bin/sh

# testbuilds.sh - 2011Feb06 - mathuin@gmail.com

# This script tests the build process so I can make sure 
# that changes do not break things.

# This script requires c10t to render a map of the world.
# c10t can be found at git://github.com/udoprog/c10t.git

: ${DATASET:="BlockIsland"}
: ${DATADIR:="Images/$DATASET"}
: ${BIOPTS:="--scale 15"}
: ${WORLDNAME:="TestWorld"}
: ${BWOPTS:="--world $WORLDNAME"}
: ${IMAGE:="$WORLDNAME.png"}
: ${MAPPER:="../c10t/build/c10t"}
: ${MAPPEROPTS:="-z -w $WORLDNAME -o $IMAGE"}

rm -rf $DATADIR $WORLDNAME $IMAGE
./BuildImages.py $BIOPTS $DATASET
./BuildWorld.py $BWOPTS $DATASET
$MAPPER $MAPPEROPTS
display $IMAGE
