import numpy as np
from math import log

def buildtree(coords):
    # initialize tree and stack
    tree = np.empty(len(coords)+1)
    tree[0] = 0
    stack = []
   
    # seed stack
    initial_indices = np.array([x for x in xrange(coords.shape[0])])
    initial_axis = 0
    initial_location = 1
    stack.append((initial_indices, initial_axis, initial_location))
    
    # work through stack
    while (len(stack) > 0):
        (indices, axis, location) = stack.pop()
        # if location is out of bounds, freak out
        if (location < 1 or location > len(tree)):
            raise IndexError, 'bad location: %d' % location
        # if only one index, we are a leaf
        if (len(indices) == 1):
            tree[location] = indices[0]
            continue
        # generate sorted index of array 
        splitarr = np.hsplit(coords[indices], 2)
        newindices = np.lexsort((splitarr[1-axis].flatten(), splitarr[axis].flatten()))
        # now calculate n, m, and r
        n = len(newindices)
        m = int(2**(int(log(n,2))))
        r = n-(m-1)
        # median?
        if (r <= (m/2)):
            median = (m-2)/2+r+1
        else:
            median = (m-2)/2+m/2+1
        tree[location] = indices[newindices[median-1]]
        if (median > 0):
            stack.append((indices[newindices[:median-1]], 1-axis, location*2))
        if (median < len(indices)):
            stack.append((indices[newindices[median:]], 1-axis, location*2+1))

    # return the tree
    return tree
