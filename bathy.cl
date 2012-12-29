// Calculate depth based on proximity

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
	  int minval = maxdepth;
	  int inval;

	  if (xval != 0) {
	    inval = indata[idx-ylen];
	    if (inval != -1 && inval < minval)
	      minval = inval;
	  }
	  if (xval != xlen) {
	    inval = indata[idx+ylen];
	    if (inval != -1 && inval < minval)
	      minval = inval;
	  }
	  if (yval != 0) {
	    inval = indata[idx-1];
	    if (inval != -1 && inval < minval)
	      minval = inval;
	  }
	  if (yval != ylen) {
	    inval = indata[idx+1];
	    if (inval != -1 && inval < minval)
	      minval = inval;
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
