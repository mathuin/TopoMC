#define MAX_K 31
#define KNN_SIZE MAX_K+1
#define STACK_SIZE 30
#define MAXINT 2147483647
#define MAXBINS 256

__kernel void knnplus(__global int *retvals, __global int *values, __global uint *tree, __global int2 *coords, const uint lentree, const uint ink, const uint usemajority, const int xfirst, const int xlen, const int xstep, const int yfirst, const int ylen, const int ystep) {
  // retvals -- OUTPUT: int array of shape (nelems)
  //            containing values for map
  // values -- INPUT: int array of shape (lentree)
  //           containing input values for interpolation
  // tree -- INPUT: uint array of shape (lentree)
  //         containing left balanced KD tree
  // coords -- INPUT: int array of shape (lentree-1,2)
  //           containing coordinates for distance calculations
  // FIXME: consider making tree an int2 containing coords!
  // would save memory and time
  // lentree -- INPUT: uint containing length of tree
  // ink -- INPUT: uint containing the number of neighbors to collect
  // usemajority -- INPUT: uint for either majority (1) or idw (0)
  // xfirst, xlen, xstep -- INPUT: ints giving dimensions of output array
  // yfirst, ylen, ystep -- INPUT: ints giving dimensions of output array

  uint xid = get_global_id(0);
  uint xsize = get_global_size(0); // width of the global size
  // xlen is the width of the dataset
  uint yid = get_global_id(1);
  uint ysize = get_global_size(1); // height of the global size
  // ylen is the height of the dataset

  // dimensional parameters
  uint nelems = xlen * ylen;

  // memory allocations
  uint searchStackNode[STACK_SIZE];
  uint searchStackAxis[STACK_SIZE];
  uint searchStackOnOff[STACK_SIZE];
  int searchStackSplit[STACK_SIZE];

  uint knnHeapID[KNN_SIZE];
  float knnHeapDist[KNN_SIZE];

  uint maxHeap, ktoobig = ink > MAX_K;
  maxHeap = select(ktoobig, ink, MAX_K);
  int retval = 0;

  // run through the elements
  for (int xidx = xid; xidx < xlen; xidx += xsize) {
    for (int yidx = yid; yidx < ylen; yidx += ysize) {
      int xval = xfirst + (xidx * xstep);
      int yval = yfirst + (yidx * ystep);
      int idx = xidx * ylen + yidx;
      int2 queryPoint = (int2) (xval, yval);
      int queryVals[2] = {queryPoint.x, queryPoint.y};
      uint countHeap = 0;
      float dist2Heap = 0;
      float diff, diff2, bestDist2 = MAXFLOAT;
      uint stackTop = 0;
      int queryValue, splitValue;

      // put root node on top of stack
      searchStackNode[stackTop] = 1;
      searchStackAxis[stackTop] = 0;
      searchStackOnOff[stackTop] = 0;
      searchStackSplit[stackTop] = MAXINT;
      stackTop++;

      // work through stack
      while (stackTop != 0) {
	// pop data off the stack
	stackTop--;
	uint currIdx = searchStackNode[stackTop];
	uint currAxis = searchStackAxis[stackTop];
	uint currOnOff = searchStackOnOff[stackTop];
	int currSplit = searchStackSplit[stackTop];

	// set indices and axes
	uint leftIdx = currIdx << 1;
	uint rightIdx = leftIdx + 1;
	uint nextAxis = 1 - currAxis;
	uint prevAxis = 1 - currAxis;

#if 0	     
	// early exit check
	if (currOnOff == 1) {
	  if (countHeap == maxHeap) {
	    queryValue = queryVals[prevAxis];
	    diff = queryValue - currSplit;
	    diff2 = diff*diff;
	    if (diff2 >= dist2Heap) {
	      // early exit approved
	      if (stackTop > 0) {
		continue;
	      }
	    }
	  }
	}
#endif

	// load current node
	uint currNode = tree[currIdx];
	int2 currCoords = coords[currNode];
	int currCoordVals[2] = {coords[currNode].x, coords[currNode].y};

	// best fit distance
	queryValue = queryVals[currAxis];
	splitValue = currCoordVals[currAxis];
	diff = splitValue - queryValue;
	diff2 = diff*diff;

	// calculate distance from median node to queryLocation
	int dx = currCoords.x - queryPoint.x;
	int dy = currCoords.y - queryPoint.y;
	float diffDist2 = (dx*dx)+(dy*dy);

	// should we add this point to the heap?
	if (countHeap < maxHeap) {
	  countHeap++;
	  knnHeapID[countHeap] = currIdx;
	  knnHeapDist[countHeap] = diffDist2;
	  if (countHeap == maxHeap) {
	    // convert array to heap
	    for (uint z = countHeap/2; z >= 1; z--) {
	      uint parentHIdx = z;
	      uint childHIdx = z << 1;
	      // compare parent to children
	      while (childHIdx <= maxHeap) {
		float parentD2 = knnHeapDist[parentHIdx];
		float childD2 = knnHeapDist[childHIdx];
		// find largest child
		if (childHIdx < maxHeap) {
		  float rightD2 = knnHeapDist[childHIdx+1];
		  if (childD2 < rightD2) {
		    childHIdx++;
		    childD2 = rightD2;
		  }
		}
		// exit if parent is larger than both children
		if (parentD2 >= childD2) {
		  break;
		}
		// demote parent by swapping with largest child
		uint tempID = knnHeapID[parentHIdx];
		float tempDist = knnHeapDist[parentHIdx];
		knnHeapID[parentHIdx] = knnHeapID[childHIdx];
		knnHeapDist[parentHIdx] = knnHeapDist[childHIdx];
		knnHeapID[childHIdx] = tempID;
		knnHeapDist[childHIdx] = tempDist;
		// update indices
		parentHIdx = childHIdx;
		childHIdx = parentHIdx<<1;
	      } // end while childHIdx <= maxHeap 
	    } // end for uint z

	    // update trim distances
	    dist2Heap = knnHeapDist[1];
	    bestDist2 = dist2Heap;
	  } // end of if countHeap == maxHeap loop
	} else if (diffDist2 < dist2Heap) {
	  // do heap replacement

	  // replace root element with new element
	  knnHeapID[1] = currIdx;
	  knnHeapDist[1] = diffDist2;
	  // demote new element
	  uint parentHIdx = 1;
	  uint childHIdx = 2;
	  // compare parent to children
	  while (childHIdx <= maxHeap) {
	    float parentD2 = knnHeapDist[parentHIdx];
	    float childD2 = knnHeapDist[childHIdx];
	    // find largest child
	    if (childHIdx < maxHeap) {
	      float rightD2 = knnHeapDist[childHIdx+1];
	      if (childD2 < rightD2) {
		childHIdx++;
		childD2 = rightD2;
	      }
	    }
	    // exit if parent is larger than both children
	    if (parentD2 >= childD2) {
	      break;
	    }
	    // demote parent by swapping with largest child
	    uint tempID = knnHeapID[parentHIdx];
	    float tempDist = knnHeapDist[parentHIdx];
	    knnHeapID[parentHIdx] = knnHeapID[childHIdx];
	    knnHeapDist[parentHIdx] = knnHeapDist[childHIdx];
	    knnHeapID[childHIdx] = tempID;
	    knnHeapDist[childHIdx] = tempDist;
	    // update indices
	    parentHIdx = childHIdx;
	    childHIdx = parentHIdx<<1;
	  } // end while childHIdx <= maxHeap 
	  // update trim distances
	  dist2Heap = knnHeapDist[1];
	  bestDist2 = dist2Heap;
	} // end of if diffDist2 < dist2Heap
	// update bestDist2
	if (queryValue <= splitValue) {
	  // do we add right subrange
	  if (diff2 < bestDist2) {
	    if (rightIdx <= lentree) {
	      searchStackNode[stackTop] = rightIdx;
	      searchStackAxis[stackTop] = nextAxis;
	      searchStackOnOff[stackTop] = 1;
	      searchStackSplit[stackTop] = splitValue;
	      stackTop++;
	    }
	  }
	  // always add left subrange
	  if (leftIdx <= lentree) {
	    searchStackNode[stackTop] = leftIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 0;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
	  }
	} else {
	  // do we add left subrange
	  if (diff2 < bestDist2) {
	    if (leftIdx <= lentree) {	 
	      searchStackNode[stackTop] = leftIdx;
	      searchStackAxis[stackTop] = nextAxis;
	      searchStackOnOff[stackTop] = 1;
	      searchStackSplit[stackTop] = splitValue;
	      stackTop++;
	    }
	  }
	  // always add right subrange
	  if (rightIdx <= lentree) {
	    searchStackNode[stackTop] = rightIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 0;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
	  }
	} // else
      } // while stacktop

      // final processing knnHeapID Dist
      if (usemajority == 1) {
	// majority algorithm
	float bins[MAXBINS];
	int bin;
	for (bin = 0; bin < MAXBINS; bin++) {
	  bins[bin] = 0.0f;
	}
	for (uint i = 1; i <= countHeap; i++) {
	  int val = values[tree[knnHeapID[i]]];
	  float sqrtdist = sqrt(knnHeapDist[i]);
	  if (sqrtdist < 0.1f) {
	    retval = val;
	    break;
	  }
	  bins[val] += 1.0f/sqrtdist;
	  if (bins[val] > bins[retval]) {
	    retval = val;
	  }
	}
      } else {
	// inverse distance weight
	float topsum = 0.0f;
	float botsum = 0.0f;
	for (uint i = 1; i <= countHeap; i++) {
	  int val = values[tree[knnHeapID[i]]];
	  float sqrtdist = sqrt(knnHeapDist[i]);
	  if (sqrtdist < 0.1f) {
	    topsum = (float) val;
	    botsum = 1.0f;
	    break;
	  }
	  topsum += ((float) (val))/sqrtdist;
	  botsum += 1.0f/sqrtdist;
	}
	retval = (int)(topsum/botsum);
      }
      retvals[idx] = retval;
    } // for int yval
  } // for int xval
}
