import numpy as np
import pyopencl as cl
import pyopencl.array as cla
from math import sqrt

debug = False

def knn(tree, coords, k, xstart, xlen, xstep, ystart, ylen, ystep):
    # tree -- left balanced KD tree of input coordinates (both)
    # coords -- input coordinates
    # k -- number of neighbors (constraints on values?)
    # xstart -- first x coordinate
    # xlen -- number of x coordinates
    # xstep -- space between coordinates
    # ystart -- first y coordinate
    # ylen -- number of y coordinates
    # ystep -- space between coordinates
    # in GPU output is passed as variable
    # here it's a list of tuples
    # [[(index, distance), (index, distance), ...], ...]
    results = []

    # in GPU this is passed as a variable
    cNodes = tree.shape[0]-1

    # counter for display purposes
    howmany = 0
    printstep = 10000
    perstep = 1
    lenresults = xlen*ylen

    # new debug
    debugIdx = -1
    debugEarlyExit = 0
    debugHeap = 0
    debugStack = 0
    debugOutput = 0

    # on GPU this app is called with (x,y) global size
    # in Python we have a double for loop
    for xidx in xrange(xlen):
        for yidx in xrange(ylen):
            currRow = xstart+xidx*xstep
            currCol = ystart+yidx*ystep
            idx = currRow * ylen + currCol
            if (idx == debugIdx):
                print "idx is %d, xidx = %d, ylen = %d, yidx = %d\n" % (idx, xidx, ylen, yidx)
            howmany += 1
            if (howmany % printstep < perstep):
                print '... visited %d tree elements of %d' % (howmany, lenresults)
            # was equal to qps[qidx]
            queryPoint = np.array([currRow, currCol])
            if (idx == debugIdx):
                print "queryVals are %f, %f\n" % (queryPoint[0], queryPoint[1])
                    
            knnHeap = [(-1, -1)]
            maxHeap = k
            countHeap = 0
            dist2Heap = 0
            bestDist2 = 9999999999
            searchStack = []
            stackTop = 0
            
            # put root search info on stack
            searchStack.append((1, 0, 0, bestDist2))
            stackTop += 1
        
            # do it!
            while (stackTop != 0):
                stackTop -= 1
                (currIdx, currAxis, currInOut, splitValue) = searchStack.pop()
                if (debugStack and idx == debugIdx):
                    print "stackTop now %d\n" % stackTop
                    print "currIdx = %d, currAxis = %d, currInOut = %d, splitValue = %f" % (currIdx, currAxis, currInOut, splitValue)
                leftIdx = currIdx << 1
                rightIdx = leftIdx + 1
                nextAxis = 1 - currAxis
                prevAxis = 1 - currAxis
                
                # early exit check
                if (currInOut == 1):
                    if (debugEarlyExit and idx == debugIdx):
                        print "checking early exit"
                    if (countHeap == maxHeap):
                        if (debugEarlyExit and idx == debugIdx):
                            print " - heap is full!"
                        # heap is full
                        # 'next line is effectively queryValue = queryPoint[prevAxis]
                        # ... ah, queryPoint[qidx][prevAxis]!
                        #     the value of the axis previously compared
                        queryValue = queryPoint[prevAxis]
                        # set splitValue to split value of parent node
                        # if (len(searchStack) != 0):
                        #     (a, b, c, splitValue) = searchStack.pop()
                        #     searchStack.append((a, b, c, splitValue))
                        diff = splitValue - queryValue
                        diff2 = diff * diff
                        if (diff2 >= dist2Heap):
                            # early exit
                            if (debugEarlyExit and idx == debugIdx):
                                print 'diff2 %f is greater than or equal to dist2Heap %f -- early exit' % (diff2, dist2Heap)
                            continue
                        else:
                            if (debugEarlyExit and idx == debugIdx):
                                print 'diff2 %f is less than dist2Heap %f -- no early exit' % (diff2, dist2Heap)
                            pass
                    else:
                        if (debugEarlyExit and idx == debugIdx):
                            print " - heap is not full!"
                        pass
                else:
                    pass

                # load current node
                currNode = tree[currIdx]
                if (idx == debugIdx):
                    print 'currNode is %d, coords[currNode] = %f, %f' % (currNode, coords[currNode][0], coords[currNode][1])

                # get best fit distance for checking child ranges
                queryValue = queryPoint[currAxis]
                splitValue = coords[currNode][currAxis]
                diff = splitValue - queryValue
                diff2 = diff * diff
                if (idx == debugIdx):
                    print 'best fit distance diff2 is ', diff2

                # calculate distance from median node to query location
                # we have to go back to coords for this
                dx = coords[currNode][0] - queryPoint[0]
                dy = coords[currNode][1] - queryPoint[1]
                diffDist2 = (dx * dx) + (dy * dy)
                if (idx == debugIdx):
                    print 'distance from median to query diffDist2 is ', diffDist2

                # do we add this to heap?
                if (countHeap < maxHeap):
                    countHeap += 1
                    knnHeap.append((currIdx, diffDist2))
                    # do we convert to max distance heap now?
                    if (countHeap == maxHeap):
                        # turn array into heap
                        for z in xrange(countHeap/2, 0, -1):
                            # demote each element in turn to proper position
                            parentHIdx = z
                            childHIdx = z << 1
                            while (childHIdx <= maxHeap):
                                parentD2 = knnHeap[parentHIdx][1]
                                childD2 = knnHeap[childHIdx][1]
                                # find largest child
                                if (childHIdx < maxHeap):
                                    rightD2 = knnHeap[childHIdx+1][1]
                                    if (childD2 < rightD2):
                                        childHIdx += 1
                                        childD2 = rightD2
                                # bail if parent is larger than largest child
                                if (parentD2 >= childD2):
                                    break
                                # demote parent by swapping with largest child
                                temp = knnHeap[parentHIdx]
                                knnHeap[parentHIdx] = knnHeap[childHIdx]
                                knnHeap[childHIdx] = temp
                                # update indices
                                parentHIdx = childHIdx
                                childHIdx = parentHIdx<<1
                        
                        # update trim distances
                        if (debug and howmany % printstep < debugperstep):
                            print 'update trim distances to ', knnHeap[1][1]
                        dist2Heap = knnHeap[1][1]
                        bestDist2 = dist2Heap;
                        if (debug and howmany % printstep < debugperstep):
                            print 'post-conversion: knnHeap now ', knnHeap
                elif (diffDist2 < dist2Heap):    
                    if (debug and howmany % printstep < debugperstep):
                        print 'heap full but diffDist2 (', diffDist2, ') < dist2Heap (', dist2Heap, ')'
                    # heap replacement
                    if (debug and howmany % printstep < debugperstep):
                        print 'replacing ', knnHeap[1], 'with ', (currIdx, diffDist2)
                    knnHeap[1] = (currIdx, diffDist2)
                    # demote new element
                    parentHIdx = 1
                    childHIdx = 2
                    while (childHIdx <= maxHeap):
                        parentD2 = knnHeap[parentHIdx][1]
                        childD2 = knnHeap[childHIdx][1]
                        # find largest child
                        if (childHIdx < maxHeap):
                            rightD2 = knnHeap[childHIdx+1][1]
                            if (childD2 < rightD2):
                                childHIdx += 1
                                childD2 = rightD2
                        # bail if parent is larger than largest child
                        if (parentD2 >= childD2):
                            break
                        # demote parent by swapping with largest child
                        temp = knnHeap[parentHIdx]
                        knnHeap[parentHIdx] = knnHeap[childHIdx]
                        knnHeap[childHIdx] = temp
                        # update indices
                        parentHIdx = childHIdx
                        childHIdx = parentHIdx<<1
                    # update trim distances
                    dist2Heap = knnHeap[1][1]
                    bestDist2 = dist2Heap;
                # update bestdist2
                if (debug and howmany % printstep < debugperstep):
                    print 'is queryValue less than or equal to splitValue?'
                if (queryValue <= splitValue):
                    if (debug and howmany % printstep < debugperstep):
                        print 'yes'
                    # check if we should add right subrange
                    if (diff2 < bestDist2):
                        if (debug and howmany % printstep < debugperstep):
                            print 'diff2 is less than bestDist2'
                        if (rightIdx <= cNodes):
                            if (debug and howmany % printstep < debugperstep):
                                print 'rightIdx is less than or equal to cNodes'
                            searchStack.append((rightIdx, nextAxis, 1, splitValue))
                            stackTop += 1
                    # always add left subrange
                    if (leftIdx <= cNodes):
                        if (debug and howmany % printstep < debugperstep):
                            print 'leftIdx is less than or equal to cNodes'
                        searchStack.append((leftIdx, nextAxis, 0, splitValue))
                        stackTop += 1
                else:
                    if (debug and howmany % printstep < debugperstep):
                        print 'no'
                    # check if we should add left subrange
                    if (diff2 < bestDist2):
                        if (debug and howmany % printstep < debugperstep):
                            print 'diff2 is less than bestDist2'
                        if (leftIdx <= cNodes):
                            if (debug and howmany % printstep < debugperstep):
                                print 'leftIdx is less than or equal to cNodes'
                            searchStack.append((leftIdx, nextAxis, 1, splitValue))
                            stackTop += 1
                    # always add right subrange
                    if (rightIdx <= cNodes):
                        if (debug and howmany % printstep < debugperstep):
                            print 'rightIdx is less than or equal to cNodes'
                        searchStack.append((rightIdx, nextAxis, 0, splitValue))
                        stackTop += 1
        
            # output results

            # it uses an offset of nelems*(i-1) for writing neighbors
            # so qidx's first neighbor is found at qidx,
            #          second neighbor is found at qidx+nelems,
            #           third neighbor is found at qidx+nelems*2
            if (debugOutput and idx == debugIdx):
                for index, pair in enumerate(knnHeap):
                    if pair[0] != -1:
                        print " Neighbor %d for %d:" % (index, idx)
                        print "  indices = %d" % pair[0]
                        print "  distances = %f" % pair[1]
            results.append([(x, sqrt(y)) for (x, y) in knnHeap[1:]])
    return results
