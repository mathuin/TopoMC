# 2014 Jul 13 Update

Due to changes in Minecraft and the USGS, this project is on hiatus.  It will be revived when the following issues are resolved:
* a simple, well-maintained API for Minecraft level creation is available for Python or Go, and
* a replacement for the USGS web services is developed

Minecraft changes very quickly, and its changes often break tools like pymclevel.  I do not have the time or the interest to roll my own equivalent to pymclevel, so I will wait until someone else does -- hopefully Mojang, but right now anyone who can keep up with the changes will do.  On the bright side, I'm really liking Go so either language is good for me.

The USGS web services have become less and less useful over the past few years as they steer customers towards the National Map viewer.  I am looking into bulk data transfers (i.e., sending them a hard drive upon which they write terabytes of data before sending it back to me) but then I have to figure out how to store that data in something like PostGIS such that I can retrieve what I need as I have from the USGS in the past.  Making this change will also inconvenience anyone else running TopoMC since they too will have to solve the data problem, but if I do it right they can use the National Map viewer to download the portion of the United States that fits their requirements instead of the whole thing like me.

I welcome any assistance with these issues.  

# Welcome to TopoMC!

The TopoMC project facilitates the construction of superficially realistic Minecraft worlds leveraging USGS, specifically the NED and NLCD datasets.

## Major changes:

* TopoMC downloads tiled data from the USGS.  These files can be quite large so they are now cached for reuse.

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

`git gdal-bin python-scipy python-gdal python-suds python-yaml python-progressbar`

Other operating systems use other packaging systems so you're on your own -- the error messages will tell you what's missing, but it's up to you to find it and install it!

## How to use TopoMC

The best way to get latitude and longitude is through Google Maps.  Choose your chunk of the planet (still limited to the United States and its possessions, alas) and right-click the upper left corner of the region you wish to model.  Select 'What's here', and the tooltip should provide the latitude and longitude in decimal degrees.  Do the same for the lower right corner of the region.  

Next, here's what to do!

1.  Import the pymclevel submodule.  Must be done once before anything else!  There are two commands here, init and update:

	```
	jmt@belle:~/git/TopoMC$ git submodule init
    jmt@belle:~/git/TopoMC$ git submodule update
	```
	
2.  (Optional) Compile the accelerated NBT module in pymclevel.

	```
	jmt@belle:~/git/TopoMC$ (cd pymclevel && python setup_nbt.py build)
	```

3.  Retrieve the region from the USGS.  The upper left latitude is the "ymax" value as seen below, and the lower right latitude is the "ymin".  For longitude, the upper left is the "xmin" while the lower right is the "xmax".

	```
	jmt@belle:~/git/TopoMC$ ./getregion.py --name Provincetown --ymax 42.0901 --xmin -70.2611 --ymin 42.0091 --xmax -70.1100
	```

4.  Prepare the region for processing.

	```
	jmt@belle:~/git/TopoMC$ ./prepregion.py --name Provincetown
	```

5.  Construct the Minecraft world based on the region.

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
