#ifdef cl_intel_printf
#pragma OPENCL EXTENSION cl_intel_printf : enable
#endif

#define MAX_K 31
#define KNN_SIZE MAX_K+1
#define STACK_SIZE 30
#define MAXBINS 256

__kernel void knnplus(__global int *retvals, __global int *values, __global uint *tree, __global float2 *coords, const uint lentree, __global float2 *base, const uint lenbase, const uint ink, const uint usemajority) {
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
  // base -- INPUT: query points
  // lenbase -- INPUT: uint containing length of query points
  // ink -- INPUT: uint containing the number of neighbors to collect
  // usemajority -- INPUT: uint for either majority (1) or idw (0)

  uint gid = get_global_id(0);
  uint gsize = get_global_size(0);

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

  uint debugIdx = 0;
  uint debugValues = 0;
  uint debugTree = 0;
  uint debugEarlyExit = 0;
  uint debugHeap = 0;
  uint debugStack = 0;
  uint debugOutput = 0;

  for (uint idx = gid; idx < lenbase; idx += gsize) {
    float2 queryPoint = base[idx];
    float queryVals[2] = {queryPoint.x, queryPoint.y};
#ifdef cl_intel_printf
    if (debugValues && idx == debugIdx) {
      printf("idx=%d queryVals are %f, %f\n", idx, queryVals[0], queryVals[1]);
    }
#endif
#ifdef cl_intel_printf      
    if (debugTree && idx == debugIdx) {
      for (uint treeind = 1; treeind < lentree; treeind++) {
	float outx = coords[tree[treeind]][0];
	float outy = coords[tree[treeind]][1];
	printf("tree: index=%d value=%d coords=%f, %f dist=%f\n", treeind, tree[treeind], outx, outy, sqrt(((outx-queryPoint.x)*(outx-queryPoint.x))+(outy-queryPoint.y)*(outy-queryPoint.y)));
      }
    }
#endif
    uint countHeap = 0;
    float dist2Heap = 0;
    float bestDist2 = MAXFLOAT;
    uint stackTop = 0;
    float queryValue, splitValue, diff, diff2;
    
    // put root node on top of stack
    searchStackNode[stackTop] = 1;
    searchStackAxis[stackTop] = 0;
    searchStackOnOff[stackTop] = 0;
    searchStackSplit[stackTop] = MAXFLOAT;
    stackTop++;
    
    // work through stack
    while (stackTop != 0) {
#ifdef cl_intel_printf
      if (debugStack && idx == debugIdx)
	for (int stackind = 0; stackind<STACK_SIZE; stackind++)
	  if (stackind < stackTop)
	    printf("--- stackind %d: index=%d axis=%d onoff=%d split=%f\n", stackind, searchStackNode[stackind], searchStackAxis[stackind], searchStackOnOff[stackind], searchStackSplit[stackind]) ;
#endif
      // pop data off the stack
      stackTop--;
      uint currIdx = searchStackNode[stackTop];
      uint currAxis = searchStackAxis[stackTop];
      uint currOnOff = searchStackOnOff[stackTop];
      float currSplit = searchStackSplit[stackTop];
#ifdef cl_intel_printf
      if (debugStack && idx == debugIdx) {
	printf("stackTop now %d\n", stackTop);
	printf("current index = %d, axis = %d, onoff = %d, split = %f\n", currIdx, currAxis, currOnOff, currSplit);
      }
#endif
      
      // set indices and axes
      uint leftIdx = currIdx << 1;
      uint rightIdx = leftIdx + 1;
      uint nextAxis = 1 - currAxis;
      uint prevAxis = 1 - currAxis;
      
      // early exit check
      if (currOnOff == 1) {
#ifdef cl_intel_printf
	if (debugEarlyExit && idx == debugIdx) {
	  printf("checking early exit\n");
	}
#endif
	if (countHeap == maxHeap) {
#ifdef cl_intel_printf
	  if (debugEarlyExit && idx == debugIdx) {
	    printf(" - heap is full!\n");
	  }
#endif
	  queryValue = queryVals[prevAxis];
	  diff = queryValue - currSplit;
	  diff2 = diff*diff;
	  if (diff2 >= dist2Heap) {
	    // early exit approved
#ifdef cl_intel_printf
	    if (debugEarlyExit && idx == debugIdx) {
	      printf(" - diff2 %f is greater than or equal to dist2Heap %f -- early exit!\n", diff2, dist2Heap);
	    }
#endif
	    continue;
#ifdef cl_intel_printf
	  } else {
	    if (debugEarlyExit && idx == debugIdx) {
	      printf(" - diff2 %f is less than dist2Heap %f -- no early exit\n", diff2, dist2Heap);
	    }
#endif
	  }
#ifdef cl_intel_printf
	} else {
	  if (debugEarlyExit && idx == debugIdx) {
	    printf(" - heap is not full -- no early exit\n");
	  }
#endif
	}
      }
      
      // load current node
      uint currNode = tree[currIdx];
      float2 currCoords = coords[currNode];
      float currCoordVals[2] = {coords[currNode].x, coords[currNode].y};
#ifdef cl_intel_printf
      if (debugValues && idx == debugIdx) {
	printf("currIdx is %d, currNode is %d, currCoordVals are %f, %f\n", currIdx, currNode, currCoordVals[0], currCoordVals[1]);
      }
#endif
      
      // best fit distance
      queryValue = queryVals[currAxis];
      splitValue = currCoordVals[currAxis];
      diff = splitValue - queryValue;
      diff2 = diff*diff;
#ifdef cl_intel_printf
      if (debugValues && idx == debugIdx) {
	printf("best fit distance diff2 is %f\n", diff2);
      }
#endif
      
      // calculate distance from median node to queryLocation
      float dx = currCoords.x - queryPoint.x;
      float dy = currCoords.y - queryPoint.y;
      float diffDist2 = (dx*dx)+(dy*dy);
#ifdef cl_intel_printf
      if (debugValues && idx == debugIdx) {
	printf("distance from median to query diffDist2 %f\n", diffDist2);
      }
#endif
      
      // should we add this point to the heap?
      if (countHeap < maxHeap) {
#ifdef cl_intel_printf
	if (debugHeap && idx == debugIdx) {
	  printf("countHeap %d < maxHeap %d -- adding (%d, %f) to the heap\n", countHeap, maxHeap, currIdx, diffDist2);
	}
#endif
	countHeap++;
	knnHeapID[countHeap] = currIdx;
	knnHeapDist[countHeap] = diffDist2;
#ifdef cl_intel_printf
	if (debugHeap && idx == debugIdx)
	  for (int heapind = 0; heapind<KNN_SIZE; heapind++)
	    if (heapind > 0 && heapind <= countHeap)
	      printf("--- NOW heapind %d: index=%d tree=%d dist=%f\n", heapind, knnHeapID[heapind], tree[knnHeapID[heapind]], knnHeapDist[heapind]);
#endif
	if (countHeap == maxHeap) {
	  // convert array to heap
#ifdef cl_intel_printf
	  if (debugHeap && idx == debugIdx) {
	    printf("countHeap %d == maxHeap %d -- heap conversion\n", countHeap, maxHeap);
	  }
#endif
#ifdef cl_intel_printf
	  if (debugHeap && idx == debugIdx)
	    for (int heapind = 0; heapind<KNN_SIZE; heapind++)
	      if (heapind > 0 && heapind <= countHeap)
		printf("--- BEFORE heapind %d: index=%d tree=%d dist=%f\n", heapind, knnHeapID[heapind], tree[knnHeapID[heapind]], knnHeapDist[heapind]);
#endif
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
#ifdef cl_intel_printf
	  if (debugHeap && idx == debugIdx)
	    for (int heapind = 0; heapind<KNN_SIZE; heapind++)
	      if (heapind > 0 && heapind <= countHeap)
		printf("--- AFTER heapind %d: index=%d tree=%d dist=%f\n", heapind, knnHeapID[heapind], tree[knnHeapID[heapind]], knnHeapDist[heapind]);
#endif
	} // end of if countHeap == maxHeap loop
      } else if (diffDist2 < dist2Heap) {
	// do heap replacement
#ifdef cl_intel_printf
	if (debugHeap && idx == debugIdx) {
	  printf("diffDist2 %f < dist2Heap %f -- heap replacement\n", diffDist2, dist2Heap);
	}
#endif
#ifdef cl_intel_printf
	if (debugHeap && idx == debugIdx)
	  for (int heapind = 0; heapind<KNN_SIZE; heapind++)
	    if (heapind > 0 && heapind <= countHeap)
	      printf("--- BEFORE heapind %d: index=%d tree=%d dist=%f\n", heapind, knnHeapID[heapind], tree[knnHeapID[heapind]], knnHeapDist[heapind]);
#endif
	
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
#ifdef cl_intel_printf
	if (debugHeap && idx == debugIdx)
	  for (int heapind = 0; heapind<KNN_SIZE; heapind++)
	    if (heapind > 0 && heapind <= countHeap)
	      printf("--- AFTER heapind %d: index=%d tree=%d dist=%f\n", heapind, knnHeapID[heapind], tree[knnHeapID[heapind]], knnHeapDist[heapind]);
#endif
      } // end of if diffDist2 < dist2Heap
	// update bestDist2
      if (queryValue <= splitValue) {
#ifdef cl_intel_printf
	if (debugStack && idx == debugIdx) {
	  printf("queryValue %f <= splitValue %f -- update bestDist2\n", queryValue, splitValue);
	}
#endif
	// do we add right subrange
	if (diff2 < bestDist2) {
#ifdef cl_intel_printf
	  if (debugStack && idx == debugIdx) {
	    printf("diff2 %f < bestDist2 %f -- add right subrange\n", diff2, bestDist2);
	  }
#endif
	  // was <=
	  if (rightIdx < lentree) {
#ifdef cl_intel_printf
	    if (debugStack && idx == debugIdx) {
	      printf("rightIdx %d < lentree %d -- put it on the stack!\n", rightIdx, lentree);
	    }
#endif
	    searchStackNode[stackTop] = rightIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 1;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
#ifdef cl_intel_printf
	    if (debugStack && idx == debugIdx) {
	      printf("stackTop now %d\n", stackTop);
	    }
#endif
	  }
	}
	// always add left subrange
	// was <=
	if (leftIdx < lentree) {
#ifdef cl_intel_printf
	  if (debugStack && idx == debugIdx) {
	    printf("leftIdx %d < lentree %d -- put it on the stack!\n", leftIdx, lentree);
	  }
#endif
	  searchStackNode[stackTop] = leftIdx;
	  searchStackAxis[stackTop] = nextAxis;
	  searchStackOnOff[stackTop] = 0;
	  searchStackSplit[stackTop] = splitValue;
	  stackTop++;
#ifdef cl_intel_printf
	  if (debugStack && idx == debugIdx) {
	    printf("stackTop now %d\n", stackTop);
	  }
#endif
	}
      } else {
#ifdef cl_intel_printf
	if (debugStack && idx == debugIdx) {
	  printf("queryValue %f > splitValue %f -- update bestDist2\n", queryValue, splitValue);
	}
#endif
	// do we add left subrange
	if (diff2 < bestDist2) {
#ifdef cl_intel_printf
	  if (debugStack && idx == debugIdx) {
	    printf("diff2 %f < bestDist2 %f -- add left subrange\n", diff2, bestDist2);
	  }
#endif
	  // was <=
	  if (leftIdx < lentree) {	 
#ifdef cl_intel_printf
	    if (debugStack && idx == debugIdx) {
	      printf("leftIdx %d < lentree %d -- put it on the stack!\n", leftIdx, lentree);
	    }
#endif
	    searchStackNode[stackTop] = leftIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 1;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
#ifdef cl_intel_printf
	    if (debugStack && idx == debugIdx) {
	      printf("stackTop now %d\n", stackTop);
	    }
#endif
	  }
	}
	// always add right subrange
	// was <=
	if (rightIdx < lentree) {
#ifdef cl_intel_printf
	  if (debugStack && idx == debugIdx) {
	    printf("rightIdx %d < lentree %d -- put it on the stack!\n", rightIdx, lentree);
	  }
#endif
	  searchStackNode[stackTop] = rightIdx;
	  searchStackAxis[stackTop] = nextAxis;
	  searchStackOnOff[stackTop] = 0;
	  searchStackSplit[stackTop] = splitValue;
	  stackTop++;
#ifdef cl_intel_printf
	  if (debugStack && idx == debugIdx) {
	    printf("stackTop now %d\n", stackTop);
	  }
#endif
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
#ifdef cl_intel_printf	  
	  if (debugOutput && idx == debugIdx) {
	    printf("sqrtdist less than 0.1, returning %d\n", val);
	  }
#endif
	  retval = val;
	  break;
	}
#ifdef cl_intel_printf	  
	if (debugOutput && idx == debugIdx) {
	  printf("adding %f to bin %d\n", 1.0f, val);
	}
#endif
	bins[val] += 1.0f; // /sqrtdist;
	if (bins[val] > bins[retval]) {
#ifdef cl_intel_printf	  
	  if (debugOutput && idx == debugIdx) {
	    printf("bins[%d] (%f) is bigger than bins[%d] (%f)\n", val, bins[val], retval, bins[retval]);
	  }
#endif
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
#ifdef cl_intel_printf	  
	  if (debugOutput && idx == debugIdx) {
	    printf("sqrtdist less than 0.1, returning %d\n", val);
	  }
#endif
	  topsum = (float) val;
	  botsum = 1.0f;
	  break;
	}
	topsum += val/sqrtdist;
	botsum += 1.0f/sqrtdist;
#ifdef cl_intel_printf	  
	if (debugOutput && idx == debugIdx) {
	  printf("adding %f to topsum (now %f)\n", val/sqrtdist, topsum);
	  printf("adding %f to botsum (now %f)\n", 1.0f/sqrtdist, botsum);
	}
#endif
      }
#ifdef cl_intel_printf	  
      if (debugOutput && idx == debugIdx) {
	printf("retval is %f/%f or %f\n", topsum, botsum, topsum/botsum);
      }
#endif
      retval = (int)(topsum/botsum);
    }
#ifdef cl_intel_printf	  
    if (debugOutput && idx == debugIdx) {
      printf("Retval for %d is %d\n", idx, retval);
    }
#endif
    retvals[idx] = retval;
  } // for uint xid
}
