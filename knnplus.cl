#pragma OPENCL EXTENSION cl_intel_printf : enable

#define MAX_K 31
#define KNN_SIZE MAX_K+1
#define STACK_SIZE 30
#define MAXINT 2147483647
#define MAXBINS 256

__kernel void knnplus(__global int *retvals, __global int *values, __global uint *tree, __global float2 *coords, const uint lentree, const uint ink, const uint usemajority, const int xfirst, const int xlen, const int xstep, const int yfirst, const int ylen, const int ystep) {
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
  float searchStackSplit[STACK_SIZE];

  uint knnHeapID[KNN_SIZE];
  float knnHeapDist[KNN_SIZE];

  uint maxHeap, ktoobig = ink > MAX_K;
  maxHeap = select(ktoobig, ink, MAX_K);
  int retval = 0;

  uint debugIdx = 116;
  uint debugPoints = 1;
  uint debugEarlyExit = 1;
  uint debugHeap = 1;
  uint debugStack = 1;
  uint debugOutput = 1;

  // run through the elements
  for (int xidx = xid; xidx < xlen; xidx += xsize) {
    for (int yidx = yid; yidx < ylen; yidx += ysize) {
      int xval = xfirst + (xidx * xstep);
      int yval = yfirst + (yidx * ystep);
      int idx = xidx * ylen + yidx;
      if (idx == debugIdx) {
	printf("idx is %d, xidx = %d, ylen = %d, yidx = %d\n", idx, xidx, ylen, yidx);
      }
      float2 queryPoint = (float2) (xval, yval);
      float queryVals[2] = {queryPoint.x, queryPoint.y};
      if (debugPoints && idx == debugIdx) {
	printf("queryVals are %f, %f\n", queryVals[0], queryVals[1]);
      }
      uint countHeap = 0;
      float dist2Heap = 0;
      float diff, diff2;
      float bestDist2 = MAXFLOAT;
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
	float currSplit = searchStackSplit[stackTop];
	if (debugStack && idx == debugIdx) {
	  printf("stackTop now %d\n", stackTop);
	  printf("current index = %d, axis = %d, onoff = %d, split = %f\n", currIdx, currAxis, currOnOff, currSplit);
	}

	// set indices and axes
	uint leftIdx = currIdx << 1;
	uint rightIdx = leftIdx + 1;
	uint nextAxis = 1 - currAxis;
	uint prevAxis = 1 - currAxis;

	// early exit check
	if (currOnOff == 1) {
	  if (debugEarlyExit && idx == debugIdx) {
	    printf("checking early exit\n");
	  }
	  if (countHeap == maxHeap) {
	    if (debugEarlyExit && idx == debugIdx) {
	      printf(" - heap is full!\n");
	    }
	    queryValue = queryVals[prevAxis];
	    diff = queryValue - currSplit;
	    diff2 = diff*diff;
	    if (diff2 >= dist2Heap) {
	      // early exit approved
	      if (debugEarlyExit && idx == debugIdx) {
		printf(" - diff2 %f is greater than or equal to dist2Heap %f -- early exit!", diff2, dist2Heap);
	      }
	      continue;
	    } else {
	      if (debugEarlyExit && idx == debugIdx) {
		printf(" - diff2 %f is less than dist2Heap %f -- no early exit\n", diff2, dist2Heap);
	      }
	    }
	  } else {
	    if (debugEarlyExit && idx == debugIdx) {
	      printf(" - heap is not full -- no early exit\n");
	    }
	  }
	}

	// load current node
	uint currNode = tree[currIdx];
	float2 currCoords = coords[currNode];
	float currCoordVals[2] = {coords[currNode].x, coords[currNode].y};
	if (debugPoints && idx == debugIdx) {
	  printf("currNode is %d, currCoordVals are %f, %f\n", currNode, currCoordVals[0], currCoordVals[1]);
	}

	// best fit distance
	queryValue = queryVals[currAxis];
	splitValue = currCoordVals[currAxis];
	diff = splitValue - queryValue;
	diff2 = diff*diff;
	if (debugPoints && idx == debugIdx) {
	  printf("best fit distance diff2 is %f\n", diff2);
	}

	// calculate distance from median node to queryLocation
	float dx = currCoords.x - queryPoint.x;
	float dy = currCoords.y - queryPoint.y;
	float diffDist2 = ((dx*dx)+(dy*dy));
	if (debugPoints && idx == debugIdx) {
	  printf("distance from median to query diffDist2 %f\n", diffDist2);
	}

	// should we add this point to the heap?
	if (countHeap < maxHeap) {
	  if (debugHeap && idx == debugIdx) {
	    printf("countHeap %d < maxHeap %d -- adding to the heap\n", countHeap, maxHeap);
	  }
	  countHeap++;
	  knnHeapID[countHeap] = currIdx;
	  knnHeapDist[countHeap] = diffDist2;
	  if (countHeap == maxHeap) {
	    // convert array to heap
	    if (debugHeap && idx == debugIdx) {
	      printf("countHeap %d == maxHeap %d -- heap conversion\n", countHeap, maxHeap);
	    }
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
	  if (debugStack && idx == debugIdx) {
	    printf("queryValue %f <= splitValue %f -- update bestDist2\n", queryValue, splitValue);
	  }
	  // do we add right subrange
	  if (diff2 < bestDist2) {
	    if (debugStack && idx == debugIdx) {
	      printf("diff2 %f < bestDist2 %f -- add right subrange\n", diff2, bestDist2);
	    }
	    if (rightIdx <= lentree) {
	      if (debugStack && idx == debugIdx) {
		printf("rightIdx %d <= lentree %d -- put it on the stack!\n", rightIdx, lentree);
	      }
	      searchStackNode[stackTop] = rightIdx;
	      searchStackAxis[stackTop] = nextAxis;
	      searchStackOnOff[stackTop] = 1;
	      searchStackSplit[stackTop] = splitValue;
	      stackTop++;
	      if (debugStack && idx == debugIdx) {
		printf("stackTop now %d\n", stackTop);
	      }
	    }
	  }
	  // always add left subrange
	  if (leftIdx <= lentree) {
	    if (debugStack && idx == debugIdx) {
	      printf("leftIdx %d <= lentree %d -- put it on the stack!\n", leftIdx, lentree);
	    }
	    searchStackNode[stackTop] = leftIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 0;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
	    if (debugStack && idx == debugIdx) {
	      printf("stackTop now %d\n", stackTop);
	    }
	  }
	} else {
	  if (debugStack && idx == debugIdx) {
	    printf("queryValue %f > splitValue %f -- update bestDist2\n", queryValue, splitValue);
	  }
	  // do we add left subrange
	  if (diff2 < bestDist2) {
	    if (debugStack && idx == debugIdx) {
	      printf("diff2 %f < bestDist2 %f -- add left subrange\n", diff2, bestDist2);
	    }
	    if (leftIdx <= lentree) {	 
	      if (debugStack && idx == debugIdx) {
		printf("leftIdx %d <= lentree %d -- put it on the stack!\n", leftIdx, lentree);
	      }
	      searchStackNode[stackTop] = leftIdx;
	      searchStackAxis[stackTop] = nextAxis;
	      searchStackOnOff[stackTop] = 1;
	      searchStackSplit[stackTop] = splitValue;
	      stackTop++;
	      if (debugStack && idx == debugIdx) {
		printf("stackTop now %d\n", stackTop);
	      }
	    }
	  }
	  // always add right subrange
	  if (rightIdx <= lentree) {
	    if (debugStack && idx == debugIdx) {
	      printf("rightIdx %d <= lentree %d -- put it on the stack!\n", rightIdx, lentree);
	    }
	    searchStackNode[stackTop] = rightIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 0;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
	    if (debugStack && idx == debugIdx) {
	      printf("stackTop now %d\n", stackTop);
	    }
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
	    if (debugOutput && idx == debugIdx) {
	      printf("sqrtdist less than 0.1, returning %d\n", val);
	    }
	    retval = val;
	    break;
	  }
	  if (debugOutput && idx == debugIdx) {
	    printf("adding %f to bin %d\n", 1.0f, val);
	  }
	  bins[val] += 1.0f; // /sqrtdist;
	  if (bins[val] > bins[retval]) {
	    if (debugOutput && idx == debugIdx) {
	      printf("bins[%d] (%f) is bigger than bins[%d] (%f)\n", val, bins[val], retval, bins[retval]);
	    }
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
	    if (debugOutput && idx == debugIdx) {
	      printf("sqrtdist less than 0.1, returning %d\n", val);
	    }
	    topsum = (float) val;
	    botsum = 1.0f;
	    break;
	  }
	  topsum += val/sqrtdist;
	  botsum += 1.0f/sqrtdist;
	  if (debugOutput && idx == debugIdx) {
	    printf("adding %f to topsum (now %f)\n", val/sqrtdist, topsum);
	    printf("adding %f to botsum (now %f)\n", 1.0f/sqrtdist, botsum);
	  }
	}
	if (debugOutput && idx == debugIdx) {
	  printf("retval is %f/%f or %f\n", topsum, botsum, topsum/botsum);
	}
	retval = (int)(topsum/botsum);
      }
      if (debugOutput && idx == debugIdx) {
	printf("Retval for %d is %d\n", idx, retval);
      }
      retvals[idx] = retval;
    } // for int yval
  } // for int xval
}
