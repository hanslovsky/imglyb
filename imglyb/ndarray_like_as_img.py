from . import accesses
from . import types
from .util import to_imglib
from jnius import JavaException, autoclass, PythonJavaClass, java_method, cast

import math
import numpy as np

PythonHelpers = autoclass('net.imglib2.python.Helpers')


class MakeAccessFunction(PythonJavaClass):
    __javainterfaces__ = ['java/util/function/LongFunction']

    def __init__(self, func):
        super(MakeAccessFunction, self).__init__()
        self.func = func

    @java_method('(J)Ljava/lang/Object;')
    def apply(self, index):
        return self.func(index)


def chunk_index_to_slices(shape, chunk_shape, cell_index):

    grid_dimensions = tuple(
        int(math.ceil(s/sh))
        for s, sh in zip(shape, chunk_shape))[::-1]

    chunk_min = []
    ndims = len(grid_dimensions)

    i = cell_index
    for d in range(ndims):
        c = i % grid_dimensions[d]
        chunk_min.append(c)
        i = (i - c)//grid_dimensions[d]

    chunk_min = chunk_min[::-1]

    slices = tuple(
        slice(c*cs, (c + 1)*cs)
        for c, cs in zip(chunk_min, chunk_shape))

    return slices


def get_chunk(array, chunk_shape, chunk_index):

    slices = chunk_index_to_slices(array.shape, chunk_shape, chunk_index)
    return np.ascontiguousarray(array[slices])


def get_chunk_access(array, chunk_shape, index, use_volatile_access=False):

    try:
        chunk = get_chunk(array, chunk_shape, index)
        target = accesses.as_array_access(chunk, volatile=use_volatile_access)
        return target

    except JavaException as e:
        print("exception    ", e)
        print("cause        ", e.__cause__)
        print("inner message", e.innermessage)
        if e.stacktrace:
            for line in e.stacktrace:
                print(line)
        raise e


def get_chunk_access_unsafe(array, chunk_shape, index):

    try:
        chunk  = get_chunk(array, chunk_shape, index)
        img    = to_imglib(chunk)
        return cast('net.imglib2.img.array.ArrayImg', img.getSource()).update(None)

    except JavaException as e:
        print("exception    ", e)
        print("cause        ", e.__cause__)
        print("inner message", e.innermessage)
        if e.stacktrace:
            for line in e.stacktrace:
                print(line)
        raise e


def as_cell_img(array, chunk_shape, *, access_type='native', **kwargs):
    access_type_function_mapping = {
        'array':  as_cell_img_with_array_accesses,
        'native': as_cell_img_with_native_accesses
    }

    if access_type not in access_type_function_mapping:
        raise Exception(f'Invalid access type: `{access_type}\'. Choose one of {access_type_function_mapping.keys()}')

    return access_type_function_mapping[access_type](array, chunk_shape, **kwargs)


# TODO is it bad style to use **kwargs to ignore unexpected kwargs?
def as_cell_img_with_array_accesses(array, chunk_shape, *, use_volatile_access=False, **kwargs):

    access_generator = MakeAccessFunction(
        lambda index: get_chunk_access(array, chunk_shape, index, use_volatile_access=use_volatile_access))

    shape = array.shape[::-1]
    chunk_shape = chunk_shape[::-1]

    img = PythonHelpers.imgWithCellLoaderFromFunc(
        shape,
        chunk_shape,
        access_generator,
        types.for_np_dtype(array.dtype, volatile=use_volatile_access),
        accesses.as_array_access(
            get_chunk(array, chunk_shape, 0),
            volatile=use_volatile_access))

    return img


# TODO is it bad style to use **kwargs to ignore unexpected kwargs?
def as_cell_img_with_native_accesses(array, chunk_shape, **kwargs):

    access_generator = MakeAccessFunction(
        lambda index: get_chunk_access_unsafe(array, chunk_shape, index))

    shape = array.shape[::-1]
    chunk_shape = chunk_shape[::-1]

    try:
        img = PythonHelpers.imgFromFunc(
            shape,
            chunk_shape,
            access_generator,
            types.for_np_dtype(array.dtype, volatile=False),
            access_factory_for(array.dtype, owning=False)(1))

    except JavaException as e:
        print("exception    ", e)
        print("cause        ", e.__cause__)
        print("inner message", e.innermessage)
        print("stack trace  ", e.stacktrace)
        if e.stacktrace:
            for line in e.stacktrace:
                print(line)
        raise e

    return img

# non-owning
ByteUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.ByteUnsafe')
CharUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.CharUnsafe')
DoubleUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.DoubleUnsafe')
FloatUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.FloatUnsafe')
IntUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.IntUnsafe')
LongUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.LongUnsafe')
ShortUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.ShortUnsafe')

def access_factory_for(dtype, owning):
    return unsafe_owning_for_dtype[dtype] if owning else unsafe_for_dtype[dtype]

unsafe_for_dtype = {
    np.dtype('complex64')  : lambda size: FloatUnsafe(2 * size),
    np.dtype('complex128') : lambda size: DoubleUnsafe(2 * size),
    np.dtype('float32')    : FloatUnsafe,
    np.dtype('float64')    : DoubleUnsafe,
    np.dtype('int8')       : ByteUnsafe,
    np.dtype('int16')      : ShortUnsafe,
    np.dtype('int32')      : IntUnsafe,
    np.dtype('int64')      : LongUnsafe,
    np.dtype('uint8')      : ByteUnsafe,
    np.dtype('uint16')     : ShortUnsafe,
    np.dtype('uint32')     : IntUnsafe,
    np.dtype('uint64')     : LongUnsafe
}

# owning
OwningByteUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningByteUnsafe')
OwningCharUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningCharUnsafe')
OwningDoubleUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningDoubleUnsafe')
OwningFloatUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningFloatUnsafe')
OwningIntUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningIntUnsafe')
OwningLongUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningLongUnsafe')
OwningShortUnsafe = autoclass('net.imglib2.img.basictypelongaccess.unsafe.owning.OwningShortUnsafe')

unsafe_owning_for_dtype = {
    np.dtype('complex64')  : lambda size: OwningFloatUnsafe(2 * size),
    np.dtype('complex128') : lambda size: OwningDoubleUnsafe(2 * size),
    np.dtype('float32')    : OwningFloatUnsafe,
    np.dtype('float64')    : OwningDoubleUnsafe,
    np.dtype('int8')       : OwningByteUnsafe,
    np.dtype('int16')      : OwningShortUnsafe,
    np.dtype('int32')      : OwningIntUnsafe,
    np.dtype('int64')      : OwningLongUnsafe,
    np.dtype('uint8')      : OwningByteUnsafe,
    np.dtype('uint16')     : OwningShortUnsafe,
    np.dtype('uint32')     : OwningIntUnsafe,
    np.dtype('uint64')     : OwningLongUnsafe
}