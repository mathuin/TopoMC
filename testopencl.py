from testbuildtree import testbuildtree
from testknn import testknn
from testknnplus import testknnplus

# final solution will do the following:
# build tree on CPU
# run knnplus on GPU

tinyatree = testbuildtree('LessTiny-a.pkl.gz')
tinybtree = testbuildtree('LessTiny-b.pkl.gz')

# real-world data
# blockislandatree = testbuildtree('BlockIsland-a.pkl.gz')
# blockislandbtree = testbuildtree('BlockIsland-b.pkl.gz')

# these both fail with wait out of resources
# -- segmentation fault
# -- I have broken it. :-(
# -- we normally use this to do the next round of testing
tinyaknn = testknn('LessTiny-a.pkl.gz')
tinybknn = testknn('LessTiny-b.pkl.gz')

# these also fail with Enqueue out of resources
tinyaknnplus = testknnplus('LessTiny-a.pkl.gz')
tinybknnplus = testknnplus('LessTiny-b.pkl.gz')
