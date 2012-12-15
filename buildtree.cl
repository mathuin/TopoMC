__kernel void buildtree(__global uint *tree, __global int2 *coords, const uint lencoords) {
  // tree -- OUTPUT: uint array of shape (lencoords+1)
  //         containing left balanced kd tree
  // coords -- INPUT: int array of shape (lencoords, 2)
  //           containing coordinates to be inserted into tree
  // lencoords -- INPUT: uint, length of coords array

  uint gid = get_global_id(0);
  uint gsize = get_global_size(0);

  for (int idx = gid; idx < lencoords; idx += gsize) {
    // the current build tree algorithm is not recursive
    // but it is still single-threaded.  oops.
  }
}
