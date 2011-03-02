from itertools import product
from mcarray import setBlockAt, setBlocksAt, setBlockDataAt, setBlocksDataAt, sealevel, fillBlocks
from time import clock

def building(x, z, elevval, length, width, height, side):
    buildingstart = clock()
    print "Constructing a building at %d, %d, %d\nwith dimensions %d, %d, %d and facing %d" % (x, z, elevval, length, width, height, side)
    x_offset = int(length/2)
    right = x-x_offset
    left = x+x_offset
    z_offset = int(width/2)
    back = z-z_offset
    front = z+z_offset
    bottom = sealevel+elevval-1
    top = bottom+height
    if (side == 0):
	doorx = x;
	doorz = front;
	doorleftx = x-1;
	doorleftz = front;
	doorrightx = x+1;
	doorrightz = front;
        # not 0x2 or 0x3 or 0x0
	doorhinge = 0x1;
	doortorchx = x;
	doortorchz = front+1;
	doortorchdata = 0x1;
	stairholex1 = right+1;
	stairholez1 = back+4;
	stairholex2 = right+1;
	stairholez2 = back+3;
	stairholex3 = right+1;
	stairholez3 = back+2;
	stairholex4 = right+1;
	stairholez4 = back+1;
	stairdata = 0x1;
    elif (side == 1):
        # facing left
	doorx = left;
	doorz = z;
	doorleftx = left;
	doorleftz = z-1;
	doorrightx = left;
	doorrightz = z+1;
	doorhinge = 0x1;
	doortorchx = left+1;
	doortorchz = z;
	doortorchdata = 0x4;
	stairholex1 = right+4;
	stairholez1 = front-1;
	stairholex2 = right+3;
	stairholez2 = front-1;
	stairholex3 = right+2;
	stairholez3 = front-1;
	stairholex4 = right+1;
	stairholez4 = front-1;
	stairdata = 0x2;
    elif (side == 2):
        # facing backwards
	doorx = x;
	doorz = back;
	doorleftx = x+1;
	doorleftz = back;
	doorrightx = x-1;
	doorrightz = back;
	doorhinge = 0x3;
	doortorchx = x;
	doortorchz = back-1;
	doortorchdata = 0x2;
	stairholex1 = left-1;
	stairholez1 = front-4;
	stairholex2 = left-1;
	stairholez2 = front-3;
	stairholex3 = left-1;
	stairholez3 = front-2;
	stairholex4 = left-1;
	stairholez4 = front-1;
	stairdata = 0x0;
    elif (side == 3):
        # right
	doorx = right;
	doorz = z;
	doorleftx = right;
	doorleftz = z+1;
	doorrightx = right;
	doorrightz = z-1;
	doorhinge = 0x2;
	doortorchx = right-1;
	doortorchz = z;
	doortorchdata = 0x3;
	stairholex1 = left-4;
	stairholez1 = back+1;
	stairholex2 = left-3;
	stairholez2 = back+1;
	stairholex3 = left-2;
	stairholez3 = back+1;
	stairholex4 = left-1;
	stairholez4 = back+1;
	stairdata = 0x3;

    # clear out all the existing space
    fillBlocks(right, length, bottom, height, back, width, "Air")
    # floor
    fillBlocks(right, length, bottom, 1, back, width, "Stone")
    # back wall
    fillBlocks(right, length, bottom, height, back, 1, "Stone")
    fillBlocks(right+1, length-2, bottom+2, height-2, back, 1, "Glass")
    # right wall
    fillBlocks(right, 1, bottom, height, back, width, "Stone")
    fillBlocks(right, 1, bottom+2, height-2, back+1, width-2, "Glass")
    # left wall
    fillBlocks(left, 1, bottom, height, back, width, "Stone")
    fillBlocks(left, 1, bottom+2, height-2, back+1, width-2, "Glass")
    # front wall
    fillBlocks(right, length, bottom, height, front, 1, "Stone")
    fillBlocks(right+1, length-2, bottom+2, height-2, front, 1, "Glass")
    # roof
    fillBlocks(right, length, top, 1, back, width, "Stone")
    fillBlocks(right+1, length-2, top, 1, back+1, width-2, "Glass")
    # now about that door
    setBlockAt(doorleftx, bottom+3, doorleftz, "Stone")
    setBlockAt(doorleftx, bottom+2, doorleftz, "Stone")
    setBlockAt(doorleftx, bottom+1, doorleftz, "Stone")
    setBlockAt(doorx, bottom+3, doorz, "Stone")
    setBlockAt(doorx, bottom+2, doorz, "Wooden Door")
    setBlockAt(doorx, bottom+1, doorz, "Wooden Door")
    setBlockDataAt(doorx, bottom+2, doorz, doorhinge | 0x8)
    setBlockDataAt(doorx, bottom+1, doorz, doorhinge)
    setBlockAt(doorrightx, bottom+3, doorrightz, "Stone")
    setBlockAt(doorrightx, bottom+2, doorrightz, "Stone")
    setBlockAt(doorrightx, bottom+1, doorrightz, "Stone")

    # stories!
    for level in xrange(bottom+4, top-3, 4):
	fillBlocks(right, length, level, 1, back, width, "Stone")
     	setBlockAt(stairholex1, level, stairholez1, "Air")
     	setBlockAt(stairholex2, level, stairholez2, "Air")
     	setBlockAt(stairholex3, level, stairholez3, "Air")
     	setBlockAt(stairholex4, level, stairholez4, "Stone Stairs")
      	setBlockAt(stairholex3, level-1, stairholez3, "Stone Stairs")
     	setBlockAt(stairholex2, level-2, stairholez2, "Stone Stairs")
     	setBlockAt(stairholex1, level-3, stairholez1, "Stone Stairs")
 	setBlockDataAt(stairholex4, level, stairholez4, stairdata)
	setBlockDataAt(stairholex3, level-1, stairholez3, stairdata)
 	setBlockDataAt(stairholex2, level-2, stairholez2, stairdata)
 	setBlockDataAt(stairholex1, level-3, stairholez1, stairdata)

    # torches
    # on the back wall
    setBlockAt(right, top, back-1, "Torch")
    setBlockDataAt(right, top, back-1, 0x2) # were 0x4
    setBlockAt(left, top, back-1, "Torch")
    setBlockDataAt(left, top, back-1, 0x2)
    # on the side walls
    setBlockAt(right-1, top, back, "Torch")
    setBlockDataAt(right-1, top, back, 0x3) # were 0x2
    setBlockAt(left+1, top, back, "Torch")
    setBlockDataAt(left+1, top, back, 0x4) # were 0x1
    setBlockAt(right-1, top, front, "Torch")
    setBlockDataAt(right-1, top, front, 0x3)
    setBlockAt(left+1, top, front, "Torch")
    setBlockDataAt(left+1, top, front, 0x4)
    # on the front wall
    setBlockAt(right, top, front+1, "Torch")
    setBlockDataAt(right, top, front+1, 0x1) # were 0x3
    setBlockAt(left, top, front+1, "Torch")
    setBlockDataAt(left, top, front+1, 0x1)
    # over the door
    setBlockAt(doortorchx, bottom+3, doortorchz, "Torch")
    setBlockDataAt(doortorchx, bottom+3, doortorchz, doortorchdata)
    # on the roof
    setBlockAt(right, top+1, back, "Torch")
    setBlockDataAt(right, top+1, back, 0x5)
    setBlockAt(left, top+1, back, "Torch")
    setBlockDataAt(left-1, top+1, back, 0x5)
    setBlockAt(right, top+1, front, "Torch")
    setBlockDataAt(right, top+1, front, 0x5)
    setBlockAt(left, top+1, front, "Torch")
    setBlockDataAt(left, top+1, front, 0x5)

    # tada
    print "... finished in %f seconds." % (clock()-buildingstart)
