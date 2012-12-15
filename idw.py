def idw(tree, values, results, majority=False):
    retval = []
    howmany = 0
    printstep = 1000
    lenresults = len(results)
    for kout in results:
        howmany += 1
        if (howmany % printstep == 0):
            print '... computed %d IDW values out of %d' % (howmany, lenresults)
        zerod = [z for (z, d) in kout if d < 1e-10]
        if zerod != []:
            idwval = int(values[int(tree[zerod[0]])])
        else:
            if majority:
                majordict = {}
                for z, d in kout:
                    v = values[int(tree[z])]
                    try:
                        # FIXME: do not use 1, use 1/distance
                        majordict[v] += 1
                    except KeyError:
                        majordict[v] = 1
                idwval = max(majordict, key=majordict.get)
            else:
                topsum = sum([values[int(tree[z])]/d for (z, d) in kout])
                botsum = sum([1/d for (z, d) in kout])
                idwval = int(topsum/botsum)
        retval.append(idwval)
    return retval
