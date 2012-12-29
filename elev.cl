__kernel void elev(__global float *retvals, __global float *values, const uint lenvalues, const float trim, const float vscale, const float sealevel) {
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
