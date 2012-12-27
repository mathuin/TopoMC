// do bathy through flood fill

#define WATER 11

__kernel void bathy(__global int *outdata, __global int *indata, const uint xlen, const uint ylen, const uint currdepth, const uint maxdepth) {
  // outdata -- OUTPUT: the next array
  // indata -- INPUT: the current array
  // xlen, ylen -- INPUT: dimensions of data 
  // currdepth -- INPUT: which depth is now being set
  // maxdepth -- INPUT: the maximum depth
  
  uint gid = get_global_id(0);
  uint gsize = get_global_size(0);

  uint nelems = xlen * ylen;

  // iterate through all the data values
  for (uint idx = gid; idx < nelems; idx += gsize) {
    // when currdepth is even, input is .x and output is .y
    // when currdepth is odd, vice versa
    uint inarr = currdepth % 2;
    int inval, outval;

    inval = indata[idx];

    // default value for output is input
    outval = indata[idx];

    if (currdepth <= maxdepth) {
      if (currdepth == 0) {
	if (indata[idx] == WATER) {
	  outval = -1;
	} else {
	  outval = 0;
	}
      } else if (currdepth == maxdepth) {
	if (indata[idx] == -1) {
	  outval = maxdepth;
	}
      } else {
	if (indata[idx] == -1) {
	  uint xval = idx / ylen;
	  uint yval = idx % ylen;

	  uint xmin, xmax, ymin, ymax;
	  if (xval == 0)
	    xmin = 0;
	  else
	    xmin = xval-1;
	  if (xval == xlen)
	    xmax = xlen;
	  else
	    xmax = xval+1;
	  if (yval == 0)
	    ymin = 0;
	  else
	    ymin = yval-1;
	  if (yval == ylen)
	    ymax = xlen;
	  else
	    ymax = yval+1;

	  // check all eight neighbors to see if any of them have values
	  int minval = maxdepth;
	  for (uint xind = xmin; xind <= xmax; xind++) {
	    for (uint yind = ymin; yind <= ymax; yind++) {
	      int inval = indata[xind*ylen+yind];
	      if (inval != -1) {
		if (inval < minval) {
		  minval = inval;
		}
	      }
	    }
	  }
	  if (minval < maxdepth) {
	    outval = minval+1;
	  }
	}
      }
      // write output
      outdata[idx] = outval;
    } // end if currdepth <= maxdepth
  } // end for uint idx
} // end kernel
