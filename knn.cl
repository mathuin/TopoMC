#define MAX_K 31
#define KNN_SIZE MAX_K+1
#define STACK_SIZE 30
#define MAXINT 2147483647

__kernel void knn(__global uint *indices, __global uint *distances, __global uint *tree, __global int2 *coords, const uint lentree, const uint ink, const int xfirst, const int xlen, const int xstep, const int yfirst, const int ylen, const int ystep) {
  // indices -- OUTPUT: uint array of shape (k*nelems)
  //            containing indices of the k nearest neighbors 
  //            for each element
  // distances -- OUTPUT: uint array of shape (k*nelems)
  //              containing squared distances to the k nearest neighbors 
  //              for each element
  // tree -- INPUT: uint array of shape (lentree)
  //         containing left balanced KD tree
  // coords -- INPUT: int array of shape (lentree-1,2)
  //           containing coordinates for distance calculations
  // FIXME: consider making tree an int2 containing coords!
  // would save memory and time
  // lentree -- INPUT: uint containing length of tree
  // ink -- INPUT: uint containing the number of neighbors to collect
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
  uint knnHeapDist[KNN_SIZE];

  uint maxHeap, ktoobig = ink > MAX_K;
  maxHeap = select(ktoobig, ink, MAX_K);

  // run through the elements
  for (int xidx = xid; xidx < xlen; xidx += xsize) {
    for (int yidx = yid; yidx < ylen; yidx += ysize) {
      int xval = xfirst + (xidx * xstep);
      int yval = yfirst + (yidx * ystep);
      int idx = xidx * ylen + yidx;
      int2 queryPoint = (int2) (xval, yval);
      int queryVals[2] = {queryPoint.x, queryPoint.y};
      uint countHeap = 0;
      uint dist2Heap = 0;
      uint bestDist2 = MAXINT;
      uint stackTop = 0;
      int queryValue, splitValue, diff, diff2;

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
		uint parentD2 = knnHeapDist[parentHIdx];
		uint childD2 = knnHeapDist[childHIdx];
		// find largest child
		if (childHIdx < maxHeap) {
		  uint rightD2 = knnHeapDist[childHIdx+1];
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
		uint tempDist = knnHeapDist[parentHIdx];
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
	    uint parentD2 = knnHeapDist[parentHIdx];
	    uint childD2 = knnHeapDist[childHIdx];
	    // find largest child
	    if (childHIdx < maxHeap) {
	      uint rightD2 = knnHeapDist[childHIdx+1];
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
	    uint tempDist = knnHeapDist[parentHIdx];
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

      // output results
      // neighbors in idx, idx+nelems, idx+2*nelems, ...
      // was countheap
      for (uint i = 1; i <= maxHeap; i++) {
	uint offset = (i-1)*nelems;
	if (i <= countHeap) {
	  indices[idx+offset] = knnHeapID[i];
	  distances[idx+offset] = knnHeapDist[i];
	} else {
	  indices[idx+offset] = 0;
	  distances[idx+offset] = MAXINT;
	}
      } // end for uint i
    } // for int yval
  } // for int xval
}
