# Welcome to TopoMC!

The TopoMC project facilitates the construction of superficially realistic Minecraft worlds leveraging USGS, specifically the NED and NLCD datasets.

## New changes

* TopoMC no longer downloads data from the USGS due to changes in their web services.  The current workaround is somewhat clumsy and awkward, but it does work.

## Old changes

* TopoMC generates Anvil worlds with full 256-block heights thanks to @codewarrior0 and his changes to mcedit/pymclevel!  Thank you!

* TopoMC also runs on Windows!  Kinda.  I think.  It works for me, anyway!  See [this](https://github.com/mathuin/TopoMC/wiki/RunningOnWindows) for more details!

* The array and world code has been replaced with region-based code which improve accuracy while saving CPU and memory.  The new commands to download, prepare, and build regions are documented below.

* GPGPU support has been added. Yes, your video card can help you build Minecraft worlds!  This latest feature relies on [PyOpenCL](http://mathema.tician.de/software/pyopencl) and its associated dependencies, and is not supported on all systems.

* The landcover code has been rewritten to support the usage of MCEdit schematics as templates for certain areas, specifically croplands (farms) and developed areas.  More information about this feature can be found [here](https://github.com/mathuin/TopoMC/wiki/UsingSchematics).

* pymclevel has been included as a submodule.  This release of pymclevel includes an accelerated NBT module which must be compiled before use, as seen below.  This module can have a significant impact on performance.

* The test dataset has been removed.

* The safehouse has been removed, but the default spawn point is still at the highest point in the dataset.

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

Due to changes in the USGS web services, TopoMC no longer downloads files directly from the USGS.  Instead, the files must be downloaded using the [National Map viewer](http://nationalmap.gov/viewer.html).

1.  Open the viewer, and find your region of interest.  Then click the "Download Data" button on the top of the browser frame to the right.

2.  Select the region with your mouse, and in the next window, select "Land Cover" and "Elevation", then click "Next".

3.  For "Land Cover", select any files marked "National Land Cover Database 2011 - Land Cover - 3x3 Degree Extents".  For the majority of cases, only one file will be required.

4.  Click the "Elevation" bar to bring up the elevation files.  These choices are more complex.  Tips to keep in mind:
    * As the page says, clicking on the products will reveal their footprints on the map. More than one product may be required to cover your entire region of interest.  Be sure to check all products required to cover your region.
	* The highest resolution will give the best results.  1/9 arc-second is better than 1/3 arc-second which is better than 1 arc second.  Not all regions have 1/9 arc-second coverage -- in those cases, select 1/3 arc-second data.
	* The only format currently supported for elevation data is IMG.
	
5.  After you click the "Next" button again, you will have one more opportunity to review your order before checkout.  When you have reviewed your order, check out and give your email address to the USGS so they can email you when your files are ready.  SAVE THAT EMAIL!  Not only will it contain links for downloading the data you requested, it will also contain the coordinates of your selection.  These will be needed for building the Minecraft world.  The coordinates will look like this:

	```
	(-70.261, 42.009), (-70.11, 42.09)
	```

## Building the Minecraft world

1.  Build the region based on the datasets retrieved from the USGS.  The values above directly translate into the command line coordinates, and don't forget the files!

	```
	jmt@belle:~/git/TopoMC$ ./getregion.py --name Provincetown --xmin -70.261 --ymin 42.009 --xmax -70.11 --ymax 42.09 --lcfile /home/jmt/nmvorders/800424/NLCD2011_LC_N42W069.zip --elfile /home/jmt/nmvorders/800424/n43w071.zip
	```

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
