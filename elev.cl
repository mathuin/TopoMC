__kernel void elev(__global int *retvals, __global int *values, const int lenvalues, const int trim, const int vscale, const int sealevel) {
  // retvals -- OUTPUT: int array of shape (lenvalues)
  //            containing values for map
  // values -- INPUT: int array of shape (lenvalues)
  //            containing original values
  // lenvalues -- INPUT: length of arrays
  // trim -- INPUT: number of meters to trim before shaping
  // vscale -- INPUT: vertical scale value
  // sealevel -- INPUT: Minecraft level corresponding to zero elevation

  uint gid = get_global_id(0);
  uint gsize = get_global_size(0);
  
  for (uint idx = gid; idx < lenvalues; idx += gsize) {
    retvals[idx] = ((values[idx]-trim)/vscale)+sealevel;
  }
}
