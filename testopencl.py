from testbuildtree import testbuildtree
from testknn import testknn
from testknnplus import testknnplus

# final solution will do the following:
# build tree on CPU
# run knnplus on GPU

tinyatree = testbuildtree('Tiny-a.pkl')
tinybtree = testbuildtree('Tiny-b.pkl')

blockislandatree = testbuildtree('BlockIsland-a.pkl')
blockislandbtree = testbuildtree('BlockIsland-b.pkl')

# these both fail with wait out of resources
# -- segmentation fault
# -- I have broken it. :-(
# -- we normally use this to do the next round of testing
tinyaknn = testknn('Tiny-a.pkl')
tinybknn = testknn('Tiny-b.pkl')

# these also fail with Enqueue out of resources
tinyaknnplus = testknnplus('Tiny-a.pkl')
tinybknnplus = testknnplus('Tiny-b.pkl')
