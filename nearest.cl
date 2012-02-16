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
