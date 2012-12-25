#define STACK_SIZE 30

__kernel void bathy(__global int *retvals, __global uint *tree, __global float2 *coords, const uint lentree, __global float2 *base, const uint lenbase, const float maxdepth) {
  // retvals -- OUTPUT: int array of shape (nelems)
  //            containing values for map
  // tree -- INPUT: uint array of shape (lentree)
  //         containing left balanced KD tree
  // coords -- INPUT: int array of shape (lentree-1,2)
  //           containing coordinates for distance calculations
  // FIXME: consider making tree an int2 containing coords!
  // would save memory and time
  // lentree -- INPUT: uint containing length of tree
  // base -- INPUT: query points
  // lenbase -- INPUT: uint containing length of query points
  // maxdepth -- INPUT: maximum depth value

  // 1.  remove idt/majority ending, replace with returning distance
  // 2.  remove heap, replace with single value

  uint gid = get_global_id(0);
  uint gsize = get_global_size(0);

  // memory allocations
  uint searchStackNode[STACK_SIZE];
  uint searchStackAxis[STACK_SIZE];
  uint searchStackOnOff[STACK_SIZE];
  float searchStackSplit[STACK_SIZE];

  for (uint idx = gid; idx < lenbase; idx += gsize) {
    float2 queryPoint = base[idx];
    float queryVals[2] = {queryPoint.x, queryPoint.y};
    float bestDist2 = MAXFLOAT;
    float worstcase = maxdepth * maxdepth;
    uint stackTop = 0;
    float queryValue, splitValue, diff, diff2;
    int retval = (int) maxdepth;
    
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
	queryValue = queryVals[prevAxis];
	diff = queryValue - currSplit;
	diff2 = diff*diff;
	if (diff2 >= bestDist2) {
	  // early exit approved
	  continue;
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

      // is this point closer than our current best point?
      if (diffDist2 < bestDist2) {
	bestDist2 = diffDist2;
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

    // return distance
    if (bestDist2 < worstcase) {
      retvals[idx] = (int) sqrt(bestDist2);
    } else {
      retvals[idx] = retval;
    }
  }
}
