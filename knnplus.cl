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

  for (uint idx = gid; idx < lenbase; idx += gsize) {
    float2 queryPoint = base[idx];
    float queryVals[2] = {queryPoint.x, queryPoint.y};
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
      stackTop--;
      uint currIdx = searchStackNode[stackTop];
      uint currAxis = searchStackAxis[stackTop];
      uint currOnOff = searchStackOnOff[stackTop];
      float currSplit = searchStackSplit[stackTop];

      // set indices and axes
      uint leftIdx = currIdx << 1;
      uint rightIdx = leftIdx + 1;
      uint nextAxis = 1 - currAxis;
      uint prevAxis = 1 - currAxis;
      
      // early exit check
      if (currOnOff == 1) {
        if (countHeap == maxHeap) {
          queryValue = queryVals[prevAxis];
          diff = queryValue - currSplit;
          diff2 = diff*diff;
          if (diff2 >= dist2Heap) {
	    // early exit approved
            continue;
          }
        }
      }
      
      // load current node
      uint currNode = tree[currIdx];
      float2 currCoords = coords[currNode];
      float currCoordVals[2] = {coords[currNode].x, coords[currNode].y};

      // best fit distance
      queryValue = queryVals[currAxis];
      splitValue = currCoordVals[currAxis];
      diff = splitValue - queryValue;
      diff2 = diff*diff;

      // calculate distance from median node to queryLocation
      float dx = currCoords.x - queryPoint.x;
      float dy = currCoords.y - queryPoint.y;
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
	    }
	  }
	  // update trim distances
	  dist2Heap = knnHeapDist[1];
	  bestDist2 = dist2Heap;
	}
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
	}
	// update trim distances
	dist2Heap = knnHeapDist[1];
	bestDist2 = dist2Heap;
      }
      if (queryValue <= splitValue) {
	if (diff2 < bestDist2) {
	  if (rightIdx < lentree) {
	    searchStackNode[stackTop] = rightIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 1;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
	  }
	}
	// always add left subrange
	// was <=
	if (leftIdx < lentree) {
	  searchStackNode[stackTop] = leftIdx;
	  searchStackAxis[stackTop] = nextAxis;
	  searchStackOnOff[stackTop] = 0;
	  searchStackSplit[stackTop] = splitValue;
	  stackTop++;
	}
      } else {
	if (diff2 < bestDist2) {
	  if (leftIdx < lentree) {
	    searchStackNode[stackTop] = leftIdx;
	    searchStackAxis[stackTop] = nextAxis;
	    searchStackOnOff[stackTop] = 1;
	    searchStackSplit[stackTop] = splitValue;
	    stackTop++;
	  }
	}
	// always add right subrange
	// was <=
	if (rightIdx < lentree) {
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
	bins[val] += 1.0f/sqrtdist; // /sqrtdist
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
	topsum += val/sqrtdist;
	botsum += 1.0f/sqrtdist;
      }
      retval = (int)(topsum/botsum);
    }
    retvals[idx] = retval;
  }
}
