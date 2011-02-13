# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright: Gael Varoquaux
# License: BSD

import numpy as np
import multiprocessing
import ctypes

_ctypes_to_numpy = {
    ctypes.c_char : np.int8,
    ctypes.c_wchar : np.int16,
    ctypes.c_byte : np.int8,
    ctypes.c_ubyte : np.uint8,
    ctypes.c_short : np.int16,
    ctypes.c_ushort : np.uint16,
    ctypes.c_int : np.int32,
    ctypes.c_uint : np.int32,
    ctypes.c_long : np.int64,
    ctypes.c_ulong : np.int64,
    ctypes.c_float : np.float32,
    ctypes.c_double : np.float64
}

_numpy_to_ctypes = dict((value, key) for key, value in
                                _ctypes_to_numpy.iteritems())

def shmem_as_ndarray(data, dtype=float):
    """ Given a multiprocessing.Array object, as created by
    ndarray_to_shmem, returns an ndarray view on the data.
    """
    dtype = np.dtype(dtype)
    size = data._wrapper.get_size()/dtype.itemsize
    arr = np.frombuffer(buffer=data, dtype=dtype, count=size)
    return arr


def ndarray_to_shmem(arr):
    """ Converts a numpy.ndarray to a multiprocessing.Array object.
    
        The memory is copied, and the array is flattened.
    """
    arr = arr.reshape((-1, ))
    data = multiprocessing.RawArray(_numpy_to_ctypes[arr.dtype.type], 
                                        arr.size)
    ctypes.memmove(data, arr.data[:], len(arr.data))
    return data
    

       
def test_ndarray_conversion():
    """ Check that the conversion to multiprocessing.Array and back works.
    """
    a = np.random.random((100, ))
    a_sh = ndarray_to_shmem(a)
    b = shmem_as_ndarray(a_sh)
    np.testing.assert_almost_equal(a, b)


def test_conversion_non_flat():
    """ Check that the conversion also works with non-flat arrays.
    """
    a = np.random.random((100, 2))
    a_flat = a.flatten()
    a_sh = ndarray_to_shmem(a)
    b = shmem_as_ndarray(a_sh)
    np.testing.assert_almost_equal(a_flat, b)


def test_conversion_non_contiguous():
    """ Check that the conversion also works with non-contiguous arrays.
    """
    a = np.indices((3, 3, 3))
    a = a.T
    a_flat = a.flatten()
    a_sh = ndarray_to_shmem(a)
    b = shmem_as_ndarray(a_sh, dtype=a.dtype)
    np.testing.assert_almost_equal(a_flat, b)



def test_no_copy():
    """ Check that the data is not copied from the multiprocessing.Array.
    """
    a = np.random.random((100, ))
    a_sh = ndarray_to_shmem(a)
    a = shmem_as_ndarray(a_sh)
    b = shmem_as_ndarray(a_sh)
    a[0] = 1
    np.testing.assert_equal(a[0], b[0])
    a[0] = 0
    np.testing.assert_equal(a[0], b[0])


################################################################################
# A class to carry around the relevant information
################################################################################

class SharedMemArray(object):
    """ Wrapper around multiprocessing.Array to share an array accross
        processes.
    """

    def __init__(self, arr):
        """ Initialize a shared array from a numpy array.

            The data is copied.
        """
        self.data = ndarray_to_shmem(arr)
        self.dtype = arr.dtype
        self.shape = arr.shape

    def __array__(self):
        """ Implement the array protocole.
        """
        arr = shmem_as_ndarray(self.data, dtype=self.dtype)
        arr.shape = self.shape
        return arr
 
    def asarray(self):
        return self.__array__()


def test_sharing_array():
    """ Check that a SharedMemArray shared between processes is indeed
        modified in place.
    """
    # Our worker function
    def f(arr):
        a = arr.asarray()
        a *= -1

    a = np.random.random((10, 3, 1))
    arr = SharedMemArray(a)
    # b is a copy of a
    b = arr.asarray()
    np.testing.assert_array_equal(a, b)
    multiprocessing.Process(target=f, args=(arr,)).run()
    np.testing.assert_equal(-b, a)


if __name__ == '__main__':

    import nose
    nose.runmodule()

