#define K 32
#define KMINUS K-1

int weighted_average(const float2 *results, const unsigned int k) {
  float sumweights = 0.0f;
  float retval = 0.0f;
  unsigned int kminus = k - 1;
  int windex;
  float notempty;

  if (isequal(results[0].x, 0.0f)) {
    sumweights = 1.0f;
    retval = results[0].y;
  } else {
    // calculate weighted average
    if (isequal(results[kminus].y, -1.0f)) {
      for (windex=0; windex<kminus; windex++) {
	notempty = isnotequal(results[windex].y, -1.0f);
	sumweights += select(notempty, (1/results[windex].x), 0);
	retval += select(notempty, (results[windex].y/results[windex].x), 0);
      }
    } else {
      for (windex=0; windex<k; windex++) {
	sumweights += (1/results[windex].x);
   	retval += (results[windex].y/results[windex].x);
      }
    }
  }
  return (int) (retval/sumweights);
}

int majority(const float2 *results, const unsigned int k) {
  int freq[256];
  int kindex, freqindex, freqvalue;
  int maxfreq = 0;
  int retval = 0;

  for (freqindex=0;freqindex<256;freqindex++) {
    freq[freqindex] = 0;
  }

  for (kindex=0;kindex<k;kindex++) {
    freqvalue = (int) results[kindex].y;
    if (freqvalue > -1) {
      freq[freqvalue]++;
    }
  }

  for (freqindex=0;freqindex<256;freqindex++) {
    if (freq[freqindex] > maxfreq) {
      maxfreq = freq[freqindex];
      retval = freqindex;
    }
  }

  return retval;
}

__kernel void nearest(__global int2 *coords, __global int *values, __global int2 *base, __global int *output, const unsigned int lencoords, const unsigned int ink, const unsigned int usemajority) {
  int gid = get_global_id(0);
  float d, dx, dy;
  float2 results[K];
  int2 mycoords, mybase = base[gid];
  unsigned int k, kminus, ktoobig = ink > K;
  int initindex, coordindex, kindex, subkindex;

  // if suggested value for k is too big, limit it to K
  k = select(ktoobig, ink, K);
  kminus = k - 1;

  for (initindex=0; initindex<k; initindex++) {
    results[initindex].x = MAXFLOAT;
    results[initindex].y = -1.0f;
  }

  for (coordindex=0; coordindex<lencoords; coordindex++) {
    mycoords = coords[coordindex];
    dx = mycoords.x-mybase.x;
    dx = dx * dx;
    dy = mycoords.y-mybase.y;
    dy = dy * dy;
    d = sqrt(dx+dy);
    // insert d into correct slot
    if (d < results[kminus].x) {
      for (kindex=0; kindex<k; kindex++) {
    	if (d < results[kindex].x) {
    	  for (subkindex=kminus; subkindex>kindex; subkindex--)
    	    results[subkindex] = results[subkindex-1];
    	  results[kindex].x = d;
    	  results[kindex].y = values[coordindex];
	  break;
    	}
      }
    }
  }
  if (usemajority == 1)
    output[gid] = majority(results, k);
  else
    output[gid] = weighted_average(results, k);
}

__kernel void trim(__global int2 *arrayin, __global int2 *arrayout, const uint split, const uint arrayinlen) 
{
  uint gid = get_global_id(0);
  uint gsize = get_global_size(0);

  for (int idx = gid; idx < arrayinlen; idx += gsize) {
    //arrayout[idx] = arrayin[idx] / split;
    arrayout[idx].x = arrayin[idx].x / split;
    arrayout[idx].y = arrayin[idx].y / split;
  }
}

__kernel void mmd(__global int2 *arrayin, 
                  __global int *gminx, __global int *gmaxx, __global int *gdupx,
                  __global int *gminy, __global int *gmaxy, __global int *gdupy,
                  __local int *lminx, __local int *lmaxx, __local int *ldupx,
                  __local int *lminy, __local int *lmaxy, __local int *ldupy,
                  const uint arrayinlen, const int checkx, const int checky) 
{
  uint gid = get_global_id(0);
  uint lid = get_local_id(0);
  uint gsize = get_global_size(0);
  uint lsize = get_local_size(0);
  uint grid = get_group_id(0);

  lminx[lid] = arrayin[gid].x;
  lmaxx[lid] = arrayin[gid].x;
  ldupx[lid] = 0;
  lminy[lid] = arrayin[gid].y;
  lmaxy[lid] = arrayin[gid].y;
  ldupy[lid] = 0;

  for (int idx = gid; idx < arrayinlen; idx += gsize) {
    int tempx = arrayin[idx].x;
    int tempy = arrayin[idx].y;
    lminx[lid] = min(lminx[lid], tempx);
    lmaxx[lid] = max(lmaxx[lid], tempx);
    if (tempx == checkx) {
      ldupx[lid] = ldupx[lid] + 1;
    }
    lminy[lid] = min(lminy[lid], tempy);
    lmaxy[lid] = max(lmaxy[lid], tempy);
    if (tempy == checky) {
      ldupy[lid] = ldupy[lid] + 1;
    }
  }

  for (int j = lsize/2; j >= 1; j /= 2) {
    barrier(CLK_LOCAL_MEM_FENCE);
    if (lid < j) {
      lminx[lid] = min(lminx[lid], lminx[lid+j]);
      lmaxx[lid] = max(lmaxx[lid], lmaxx[lid+j]);
      ldupx[lid] += ldupx[lid+j];
      lminy[lid] = min(lminy[lid], lminy[lid+j]);
      lmaxy[lid] = max(lmaxy[lid], lmaxy[lid+j]);
      ldupy[lid] += ldupy[lid+j];
    }
  }

  if (lid == 0) {
    gminx[grid] = lminx[lid];
    gmaxx[grid] = lmaxx[lid];
    gdupx[grid] = ldupx[lid];
    gminy[grid] = lminy[lid];
    gmaxy[grid] = lmaxy[lid];
    gdupy[grid] = ldupy[lid];
  }
}
