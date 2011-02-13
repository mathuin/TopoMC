#!/bin/bash

# warpelev.sh - 2011Jan24 - mathuin@gmail.com

# This script warps the elevation file for a particular region
# to match the land cover file.

# example:  ./warpelev.sh BlockIsland

function usage() {
    echo "Usage: $0 --region [region]"
    exit
}

if [ $# -eq 2 ] && [ "$1" = "--region" ]; then
    region=$2
else
    usage
fi

function processLayerID() {
    origstring=$1
    layerid=`echo $origstring | sed -e "s/\(...\)\(..\)\(.\)\(.\)/\1 \2 \3 \4/"`
    set -- $layerid
    productid=$1
    if [ "$productid" = "L01" ]; then
	foundl01=$origstring
    elif [ "$productid" = "ND3" ]; then
	foundnd3=$origstring
    elif [ "$productid" = "NED" ]; then
	foundned=$origstring
    else
	echo "Unknown product ID found!"
	exit
    fi
    imagetype=$2
    if [ "$imagetype" = "02" ]; then
	imagesuffix=tif
    else
	echo "Unknown image format found!"
	exit
    fi
    metatype=$3
    if [ "$metatype" = "H" ]; then
	foundhtml=true
    elif [ "$metatype" = "T" ]; then
	foundtxt=true
    elif [ "$metatype" = "X" ]; then
	foundxml=true
    else
	echo "Unknown metadata format found!"
	exit
    fi
    compresstype=$4
    if [ "$compresstype" = "Z" ]; then
	extractcmd=unzip
	compresssuffix=zip
    elif [ "$compresstype" = "T" ]; then
	extractcmd="tar xf"
	compresssuffix=tgz
    else
	echo "Unknown compression format found!"
	exit
    fi
}

regiondir="Datasets/$region"
if [ -d $regiondir ]; then
    regionfilelist=`ls $regiondir | xargs echo`
else
    echo "There is no region directory for $region."
    exit
fi

# extract the images 
for regionfile in $regionfilelist; do
    fullname=$regiondir/$regionfile
    if [ -d $fullname ]; then
	
	processLayerID $regionfile
	# now do something
	datafiles=`ls $fullname`
	for datafile in $datafiles; do
	    if [ "${datafile#*.}" = "$compresssuffix" ]; then
		basename=`basename $datafile .$compresssuffix`
		# FIXME: cannot unzip single file?!
		#`(cd $fullname && unzip $datafile $basename/$basename.$imagesuffix)`
		(cd $fullname && unzip -oqq $datafile)
		# and now we have the imagename
		imagename=$fullname/$basename/$basename.$imagesuffix
		if [ ! -f $imagename ]; then
		    echo "Image name $imagename not found!"
		    exit
		fi
	    else
		echo "$datafile is not of the correct type"
	    fi
	done
    else
	echo "$file found but ignored"
    fi
done    

# did we find what we needed
if [ "x${foundl01}" = "x" ]; then
    echo "No landcover directory found!"
    exit
else
    foundlc=$foundl01
fi
if [ "x${foundnd3}" = "x" ]; then
    if [ "x${foundned}" = "x" ]; then
	echo "No elevation directory found!"
    else
	foundelev=$foundned
    fi
else
    foundelev=$foundnd3
fi

# foundlc and foundelev have the layerids
processLayerID $foundlc
# FIXME: not multi-directory safe!
lcimage=`find $regiondir/$foundlc/ -name "*.$imagesuffix" -print`
processLayerID $foundelev
# FIXME: not multi-directory safe!
elevimage=`find $regiondir/$foundelev/ -name "*.$imagesuffix" -print`
elevorig=${elevimage}-orig
elevnew=${elevimage}-new
# archive the original
if [ ! -f ${elevorig} ]; then
    cp ${elevimage} ${elevorig}
fi
# populate PRF with SRS
gdalinfo ${lcimage} | sed -e "1,/Coordinate System is:/d" -e "/Origin =/,\$d" | xargs echo > /tmp/crazy.prf

# now warp the elevation image
gdalwarp -t_srs /tmp/crazy.prf -r cubic ${elevorig} ${elevnew} && mv ${elevnew} ${elevimage}

# clean up
rm /tmp/crazy.prf
