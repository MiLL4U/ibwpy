"""
IBWPy
=====

Provides
  1. Functions for reading/writing Igor binary wave (*.ibw) directly
  2. Interfaces to edit ibw files as NumPy array
"""

import numpy as np
from typing import Union, List, Tuple
from .main import DTypes, DEFAULT_DTYPE
from .main import BinaryWave5, BinaryWaveHeader5, BinaryWave5Loader


def make(shape: Union[List[int], Tuple[int, ...]],
         name: str, dtype: DTypes = DEFAULT_DTYPE) -> BinaryWave5:
    shape_tuple = tuple(shape)
    header = BinaryWaveHeader5(shape=shape_tuple, name=name, dtype=dtype)
    zeros = np.zeros(shape, dtype=dtype)
    res = BinaryWave5(ibw_header=header, wave_values=zeros)
    return res


def from_nparray(array: np.ndarray, name: str) -> BinaryWave5:
    header = BinaryWaveHeader5(shape=array.shape, name=name,
                               dtype=str(array.dtype))
    res = BinaryWave5(ibw_header=header, wave_values=array)
    return res


def load(path: str) -> BinaryWave5:
    loader = BinaryWave5Loader(path)
    res = loader.load()
    return res
