# 2014 Jul 13 Update

Due to changes in Minecraft and the USGS, this project is on hiatus.  It will be revived when the following issues are resolved:
* a simple, well-maintained API for Minecraft level creation is available for Python or Go, and
* a replacement for the USGS web services is developed

Minecraft changes very quickly, and its changes often break tools like pymclevel.  I do not have the time or the interest to roll my own equivalent to pymclevel, so I will wait until someone else does -- hopefully Mojang, but right now anyone who can keep up with the changes will do.  On the bright side, I'm really liking Go so either language is good for me.

The USGS web services have become less and less useful over the past few years as they steer customers towards the National Map viewer.  I am looking into bulk data transfers (i.e., sending them a hard drive upon which they write terabytes of data before sending it back to me) but then I have to figure out how to store that data in something like PostGIS such that I can retrieve what I need as I have from the USGS in the past.  Making this change will also inconvenience anyone else running TopoMC since they too will have to solve the data problem, but if I do it right they can use the National Map viewer to download the portion of the United States that fits their requirements instead of the whole thing like me.

I welcome any assistance with these issues.  

# Welcome to TopoMC!

The TopoMC project facilitates the construction of superficially realistic Minecraft worlds leveraging USGS, specifically the NED and NLCD datasets.

## New changes

* TopoMC no longer downloads data from the USGS due to changes in their web services.  The current workaround is somewhat clumsy and awkward, but it does work.

## Before running TopoMC

You will need some additional software installed on your system before TopoMC can run.  On Ubuntu (precise pangolin), the following packages need to be installed:  

`git gdal-bin python-scipy python-gdal python-yaml`

Other operating systems use other packaging systems so you're on your own -- the error messages will tell you what's missing, but it's up to you to find it and install it!

## Installation

Next, here's what to do!

1.  Import the pymclevel submodule.  Must be done once before anything else!

	```
	jmt@belle:~/git/TopoMC$ git submodule update --init
	```
	
2.  (Optional) Compile the accelerated NBT module in pymclevel.

	```
	jmt@belle:~/git/TopoMC$ (cd pymclevel && python setup_nbt.py build)
	```

## Retrieving the map data

Due to changes in the USGS web services, TopoMC no longer downloads files directly from the USGS.  Instead, the files must be downloaded using the [National Map viewer](http://viewer.nationalmap.gov/viewer/).

1.  Open the viewer, and find your region of interest.  Then click the "Download Data" button on the top of the browser frame to the right.

2.  Select the region with your mouse, and in the next window, select "Land Cover" and "Elevation", then click "Next".

3.  For "Land Cover", select any files marked "National Land Cover Database 2011 - Land Cover - 3x3 Degree Extents".
    * As the page says, clicking on the products will reveal their footprints on the map. More than one product may be required to cover your entire region of interest.  Be sure to select all relevant products required to cover your region.  For the majority of cases, only one file will be required for land cover.
	
4.  Click the "Elevation" bar to bring up the elevation files.  These choices are more complex.  Tips to keep in mind:
	* More regions will require multiple elevation files than multiple land cover files, so it is even more important to select all relevant products for elevation.
	* The highest resolution will give the best results.  1/9 arc-second is better than 1/3 arc-second which is better than 1 arc second.  Not all regions have 1/9 arc-second coverage -- in those cases, select 1/3 arc-second data.
	* The only format currently supported for elevation data is IMG.
	
5.  After you click the "Next" button again, you will have one more opportunity to review your order before checkout.  When you have reviewed your order and confirmed that you indeed have all the files necessary to cover your region of interest, check out and give your email address to the USGS so they can email you when your files are ready.  SAVE THAT EMAIL!  Not only will it contain links for downloading the data you requested, it will also contain the coordinates of your selection.  These will be needed for building the Minecraft world.  The coordinates will look like this:

	```
	(-70.261, 42.009), (-70.11, 42.09)
	```

## Building the Minecraft world

1.  Build the region based on the datasets retrieved from the USGS.  The values above directly translate into the command line coordinates, and don't forget the files!

	```
	jmt@belle:~/git/TopoMC$ ./getregion.py --name Provincetown --xmin -70.261 --ymin 42.009 --xmax -70.11 --ymax 42.09 --lcfile ~/Downloads/NLCD2011_LC_N42W069.zip,~/Downloads/NLCD2011_LC_N39W069.zip --elfile ~/Downloads/n43w071.zip
    ```
	
	Note that multiple files are separated by commas.

2.  Prepare the region for processing.

	```
	jmt@belle:~/git/TopoMC$ ./prepregion.py --name Provincetown
	```

3.  Construct the Minecraft world based on the region.

	```
	jmt@belle:~/git/TopoMC$ ./buildregion.py --name Provincetown
	```

### Geek knobs for GetRegion.py

GetRegion.py has a number of optional arguments not shown above.

* Tile size can be changed.
    The default tile size is 256x256, but it can be changed.  The only requirement is that it be a multiple of 16.  An example would be "--tilesize 64".  Decreasing the tile size will increase the number of jobs while correspondingly decreasing the size of those jobs which can help with memory issues.  Increasing the tile size will decrease the number of jobs while correspondingly increasing the size of those jobs which can help with speed issues.  Only change the tile size if all other changes are not having the desired effect.

* Horizontal and vertical scaling can be changed.
    The horizontal and vertical scale, both of which default to 6, can be changed independently.  The minimum horizontal scale is 1 with a practical maximum of 30.  The minimum vertical scale is more complex, and essentially depends on the elevation change between the highest point in the region and sea level.  An example scale would be "--scale 1 --vscale 1".  Should the requested scale exceed valid parameters, the software will adjust the scale after informing the user.

* Sealevel and maximum depth can be changed.
    Sometimes the minimum vertical scale is too high.  One way to improve this situation is to lower the sealevel from its default of 64 to something lower such as 16 or 8.  The maximum depth should also be lowered as well.  Keep in mind that this may have unexpected effects on ore distribution!  An example sealevel and maximum depth would be "--sealevel 16 --maxdepth 8".

* Elevation can be trimmed!
    When lowering the sealevel isn't enough to reach your desired vertical scale, excess elevation can be trimmed.  Elevation is considered excess if it is between sea level and the lowest point on the region.  For example, if a region were selected such that its surface was between 200 and 300 meters above sea level, the 200 meters between sea level and the lowest point on the region could be trimmed.  An example trim would be "--trim 200".  If the trim value requested exceeds the valid limits, the software will adjust the trim value to the maximum allowed after informing the user.
