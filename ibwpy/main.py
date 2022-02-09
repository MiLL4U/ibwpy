from __future__ import annotations

import datetime
import re
import struct
from copy import deepcopy
from functools import reduce
from typing import List, Tuple, Union, cast

import numpy as np
from typing_extensions import Literal, TypedDict

BIN_HEADER_SIZE = 64
WAVE_HEADER_SIZE = 320
VALID_DTYPES = ['float32', 'float64', 'int8', 'int16', 'int32']
DTypes = Literal['float32', 'float64', 'int8', 'int16', 'int32']

WAVETYPES = {0: 'text', 1: 'complex', 2: 'float32',
             4: 'float64', 8: 'int8', 0x10: 'int16', 0x20: 'int32',
             0x40: 'unsigned'}
DTYPE_IDS = {'float32': 2, 'float64': 4,
             'int8': 8, 'int16': 0x10, 'int32': 0x20}
DTYPE_BYTES = {'float32': 4, 'float64': 8,
               'int8': 1, 'int16': 2, 'int32': 4}
DATETIME_OFFSET = datetime.datetime(1904, 1, 1, 0, 0, 0)

MAX_WAVE_NAME_LENGTH = 31
MAX_NDIM = 4
DEFAULT_WAVE_NAME = 'wave'
DEFAULT_DTYPE: DTypes = 'float32'
TEXT_ENCODE = 'utf-8'
TEXT_ENCODE_2ND = 'shift_jis'
DEFAULT_EOL = '\n'

DEFAULT_AXES_UNIT = ('', '', '', '')
DEFAULT_AXES_START = (0., 0., 0., 0.)
DEFAULT_AXES_DELTA = (1., 1., 1., 1.)
DEFAULT_AXES_LABEL_SIZE = (0, 0, 0, 0)


def decode_unicode(text_buf: bytes):
    try:
        res = text_buf.decode(TEXT_ENCODE)
    except UnicodeDecodeError:
        res = text_buf.decode(TEXT_ENCODE_2ND)
    return res


class BinaryWave5:
    def __init__(self,
                 ibw_header: BinaryWaveHeader5,
                 wave_values: np.ndarray,
                 data_unit: str = '',
                 axes_unit: List[str] = None,
                 dependency_formula: str = '',
                 note: str = '',
                 # axes_label: List[List[str]] = None,
                 ) -> None:
        self.__header = ibw_header
        if self.__header.dtype != wave_values.dtype:
            raise TypeError(
                'Data type of wave_values ({})'
                'does not match with ibw_header ({})'
                .format(wave_values.dtype, self.__header.dtype))
        self.__values = wave_values
        self.__data_unit = data_unit
        self.__axes_unit = axes_unit if axes_unit \
            else ['' for _ in range(wave_values.ndim)]

        dependency_formula = self.__convert_eol(dependency_formula)
        self.__dependency_formula = dependency_formula
        self.__header.formula_size = len(dependency_formula)

        note = self.__convert_eol(note)
        self.__note = note
        self.__header.note_size = len(note)

    def __update_modify_time(self):
        self.__header.update_modify_time()

    def __str__(self) -> str:
        name = '{} (IgorBinaryWave)\n'.format(self.name)
        return name + str(self.__values)

    def __add__(self, other: Union[BinaryWave5, np.ndarray, int, float,
                                   List[int], List[float]]) -> BinaryWave5:
        if isinstance(other, BinaryWave5):
            other = other.__values
        res_array = self.array + other
        res = deepcopy(self)
        res.__values = res_array

        res.__update_dtype()
        res.__update_modify_time()
        return res

    def __sub__(self, other: Union[BinaryWave5, np.ndarray, int, float,
                                   List[int], List[float]]) -> BinaryWave5:
        if isinstance(other, BinaryWave5):
            other = other.__values
        res_array = self.array - other
        res = deepcopy(self)
        res.__values = res_array

        res.__update_dtype()
        res.__update_modify_time()
        return res

    def __mul__(self, other: Union[BinaryWave5, np.ndarray, int, float,
                                   List[int], List[float]]) -> BinaryWave5:
        if isinstance(other, BinaryWave5):
            other = other.__values
        res_array = self.array * other
        res = deepcopy(self)
        res.__values = res_array

        res.__update_dtype()
        res.__update_modify_time()
        return res

    def __truediv__(self, other: Union[BinaryWave5, np.ndarray, int, float,
                                       List[int], List[float]]) -> BinaryWave5:
        if isinstance(other, BinaryWave5):
            other = other.__values
        res_array = self.array / other
        res = deepcopy(self)
        res.__values = res_array

        res.__update_dtype()
        res.__update_modify_time()
        return res

    def __len__(self) -> int:
        return len(self.__values)

    def __getitem__(self, key) -> np.ndarray:
        return self.__values[key]

    def __setitem__(self, key, value) -> BinaryWave5:
        res = self.__values.copy()
        res[key] = value
        self.__values = res

        self.__update_dtype()
        self.__update_modify_time()
        return self

    @property
    def name(self) -> str:
        return self.__header.name

    def rename(self, name: str) -> BinaryWave5:
        self.__header.rename(name)

        self.__update_modify_time()
        return self

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.__header.shape

    def reshape(self, shape: Union[List[int], Tuple[int, ...]]) -> BinaryWave5:
        shape_tuple = tuple(shape)
        self.__header.reshape(shape_tuple)
        self.__values = self.__values.reshape(shape_tuple)

        # following informations will initialized
        self.__axes_unit = ['' for i in range(self.__values.ndim)]
        # TODO: support dimension label
        """
        self.__axes_label = ...
        """

        self.__update_modify_time()
        return self

    @property
    def dtype(self) -> str:
        return self.__header.dtype

    def __update_dtype(self) -> BinaryWave5:
        self.__header.set_dtype(str(self.__values.dtype))
        return self

    def change_dtype(self, dtype: str) -> BinaryWave5:
        if not self.__header.is_valid_dtype(dtype):
            raise TypeError("invalid data type")
        self.__values = self.__values.astype(dtype)

        self.__update_dtype()
        self.__update_modify_time()
        return self

    @property
    def array(self) -> np.ndarray:
        return self.__values

    def set_values(self,
                   values: Union[np.ndarray, BinaryWave5, int, float]
                   ) -> BinaryWave5:
        if isinstance(values, BinaryWave5):
            set_values = values.array
        elif isinstance(values, np.ndarray):
            set_values = values
        elif isinstance(values, (int, float)):
            set_values = np.full(self.shape, values)
        else:
            raise TypeError('IgorBinaryWave or NumPy array is required')
        if set_values.shape != tuple(self.shape):
            raise ValueError('shape of array does not match to original shape')
        self.__values = set_values

        self.__update_dtype()
        self.__update_modify_time()
        return self

    @property
    def ndim(self) -> int:
        return self.__header.ndim

    @property
    def dependency_formula(self) -> str:
        return self.__dependency_formula

    def __convert_eol(self, string, to=DEFAULT_EOL):
        return re.sub(r'\r\n|\r|\n', to, string)

    def set_dependency_formula(self, formula: str) -> BinaryWave5:
        if not isinstance(formula, str):
            raise TypeError('a string is required')
        formula = self.__convert_eol(formula)
        self.__dependency_formula = formula
        self.__header.formula_size = len(formula)

        self.__update_modify_time()
        return self

    @property
    def data_unit(self) -> str:
        return self.__data_unit

    def set_data_unit(self, unit: str) -> BinaryWave5:
        if not isinstance(unit, str):
            raise TypeError('a string is required as unit')

        self.__header.set_data_unit(unit)
        self.__data_unit = unit

        self.__update_modify_time()
        return self

    @property
    def axes_unit(self) -> Tuple[str, ...]:
        return tuple(self.__axes_unit)

    def set_axis_unit(self, axis_index: int, unit: str) -> BinaryWave5:
        if not isinstance(unit, str):
            raise TypeError('a string is required as unit')

        self.__header.set_axis_unit(axis_index, unit)
        self.__axes_unit[axis_index] = unit

        self.__update_modify_time()
        return self

    def set_axis_scale(self, axis_index: int,
                       start: Union[float, int],
                       delta: Union[float, int]) -> BinaryWave5:
        start = float(start)
        delta = float(delta)
        self.__header.set_axis_scale(axis_index, start, delta)

        self.__update_modify_time()
        return self

    def calculated_axis_wave(self, axis_index: int) -> np.ndarray:
        return self.__header.calculated_axis_wave(axis_index)

    @property
    def data_scale(self) -> Union[Tuple[float, float], None]:
        return self.__header.data_scale

    def set_data_scale(self,
                       max_: Union[float, int],
                       min_: Union[float, int]) -> BinaryWave5:
        max_ = float(max_)
        min_ = float(min_)
        self.__header.set_data_scale(max_, min_)

        self.__update_modify_time()
        return self

    @property
    def note(self) -> str:
        return self.__note

    def set_note(self, note: str) -> BinaryWave5:
        if not isinstance(note, str):
            raise TypeError('a string is required')
        note = self.__convert_eol(note)
        self.__note = note
        self.__header.note_size = len(note)

        self.__update_modify_time()
        return self

    @property
    def creation_time(self) -> datetime.datetime:
        return self.__header.creation_time

    def set_creation_time(self, time: datetime.datetime) -> BinaryWave5:
        if not isinstance(time, datetime.datetime):
            raise TypeError("datetime.datetime object is required")
        self.__header.set_creation_time(time)
        return self

    def __update_creation_time(self) -> BinaryWave5:
        self.__header.update_creation_time()
        return self

    @property
    def modify_time(self) -> datetime.datetime:
        return self.__header.modify_time

    def __initialize_modify_time(self) -> BinaryWave5:
        self.__header.initialize_modify_time()
        return self

    def duplicate(self, name: str) -> BinaryWave5:
        res = deepcopy(self)
        res.rename(name)
        res.__update_creation_time()
        res.__initialize_modify_time()
        return res

    def save(self, path: str) -> None:
        header_buf = self.__header.buffer
        values_buf = self.__values.tobytes(order='F')

        dependency_formula_buf = bytes(
            self.__dependency_formula, encoding=TEXT_ENCODE)
        note_buf = bytes(self.__note, encoding=TEXT_ENCODE)

        if not self.__header.data_unit:
            ex_data_unit_buf = bytes(self.data_unit, encoding=TEXT_ENCODE)
        else:
            ex_data_unit_buf = b''

        short_dim_units = self.__header.axes_unit
        dim_units = self.axes_unit
        ex_dim_units_bufs = [bytes(dim_unit, encoding=TEXT_ENCODE)
                             if not short_dim_unit else b''
                             for dim_unit, short_dim_unit
                             in zip(dim_units, short_dim_units)]
        ex_dim_units_buf = reduce(lambda x, y: x + y, ex_dim_units_bufs)
        # TODO: support dimension label
        # dimension_label_bufs = ...

        buffer = header_buf + values_buf \
            + dependency_formula_buf + note_buf \
            + ex_data_unit_buf + ex_dim_units_buf

        with open(path, mode='wb') as f:
            f.write(buffer)


class BinaryWave5Loader:
    def __init__(self, path: str) -> None:
        self.path = path

    def __has_valid_checksum(self) -> bool:
        with open(self.path, mode='rb') as f:
            header_buf = f.read(BIN_HEADER_SIZE + WAVE_HEADER_SIZE)
            values = np.array(struct.unpack("192h", header_buf))
            checksum = np.sum(values, dtype=np.int16)

            return checksum == 0

    def load(self) -> BinaryWave5:
        if not self.__has_valid_checksum():
            raise ValueError('bad checksum')

        header_loader = BinaryWaveHeader5Loader()
        with open(self.path, mode='rb') as f:
            bin_header_buf = f.read(BIN_HEADER_SIZE)
            wave_header_buf = f.read(WAVE_HEADER_SIZE)
            header = header_loader.load_from_buffer(
                bin_header_buf, wave_header_buf)
            section_sizes = header.section_sizes

            values_buf = f.read(section_sizes['value_size'])
            values = np.frombuffer(values_buf, dtype=header.dtype)
            values_array = np.reshape(values, list(reversed(header.shape))).T

            dependency_formula_buf = f.read(section_sizes['formula_size'])
            dependency_formula = decode_unicode(dependency_formula_buf)

            note_buf = f.read(section_sizes['note_size'])
            note = decode_unicode(note_buf)

            ex_data_unit = decode_unicode(
                f.read(section_sizes['ex_data_unit_size']))
            data_unit = header.data_unit if header.data_unit else ex_data_unit

            ex_axes_unit = [decode_unicode(f.read(size))
                            for size in section_sizes['ex_axes_unit_size']]
            axes_unit = [short_unit if short_unit else ex_unit
                         for short_unit, ex_unit
                         in zip(header.axes_unit, ex_axes_unit)]

            # TODO: support dimension label
            if section_sizes['axes_label_size'] != (0, 0, 0, 0):
                print('Warning: axis labels are not supported')

                # TODO: delete when dimension labels are supported
                header.initialize_axis_label_size()

            """
            axes_label_buf = [f.read(size)
                              for size in section_sizes['axes_label_size']]
            """

        res = BinaryWave5(ibw_header=header,
                          wave_values=values_array,
                          data_unit=data_unit,
                          axes_unit=axes_unit,
                          dependency_formula=dependency_formula,
                          note=note)
        return res


class BinaryWaveHeader5:
    def __init__(
            self, shape: Tuple[int, ...], name: str, dtype: str = DEFAULT_DTYPE,
            formula_size: int = 0, note_size: int = 0,
            data_unit: Union[str, int] = '',  # unit or size (if extended unit)
            axes_unit: Tuple[Union[str, int], Union[str, int],  # default: '' x4
                             Union[str, int], Union[str, int]] = None,
            axes_start: Tuple[float, float, float,
                              float] = None,  # default: 0. x 4
            axes_delta: Tuple[float, float, float,
                              float] = None,  # default: 1. x 4
            axes_label_size: Tuple[int, int, int,
                                   int] = None,  # default: 0 x 4
            creation_time: datetime.datetime = datetime.datetime.now(),
            modify_time: datetime.datetime = DATETIME_OFFSET,
            data_scale: Union[Tuple[float, float], None] = None) -> None:
        if not self.is_valid_name(name):
            raise ValueError('invalid name')
        self.__name = name
        if not self.is_valid_dtype(dtype):
            raise ValueError('invalid data type')
        self.__dtype = dtype
        if not self.__is_valid_shape(shape):
            raise ValueError('invalid shape')
        self.__shape = shape

        self.formula_size = formula_size  # must updated in loading/writing wave
        self.note_size = note_size  # must updated in loading/writing wave
        self.__data_unit = data_unit
        self.__axes_unit = axes_unit if axes_unit else DEFAULT_AXES_UNIT
        """
        <NOTE>
        data_unit stores a data unit string when (data unit length) <= 3 or
        the size of a data unit string when (data unit length) > 3.
        It is the same in axes_unit (list of dimension units).
        """
        self.__axes_start = axes_start if axes_start else DEFAULT_AXES_START
        self.__axes_delta = axes_delta if axes_delta else DEFAULT_AXES_DELTA
        self.__axes_label_size = axes_label_size if axes_label_size  \
            else DEFAULT_AXES_LABEL_SIZE
        self.__creation_time = creation_time
        self.__modify_time = modify_time
        self.__data_scale = data_scale

    @property
    def name(self) -> str:
        return self.__name

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        ub_removed = name.replace('_', '')
        if not ub_removed.encode(TEXT_ENCODE).isalnum():
            raise ValueError('all characters in name must be '
                             'alphabet, digit, or underscore')
        if not name[0].isalpha():
            raise ValueError('name must start with an alphabet')
        if len(name) > MAX_WAVE_NAME_LENGTH:
            raise ValueError(
                'max length of name is {}'.format(MAX_WAVE_NAME_LENGTH))
        return True

    def rename(self, name: str) -> BinaryWaveHeader5:
        if not self.is_valid_name(name):
            raise ValueError('invalid name')
        self.__name = name
        return self

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.__shape

    def __is_valid_shape(self, shape: Tuple[int, ...]) -> bool:
        if not isinstance(shape, tuple):
            raise TypeError(
                'shape must be passed as a tuple of positive integer(s)')
        if not all([isinstance(size, int) and size > 0 for size in shape]):
            raise ValueError(
                'shape must be passed as a tuple of positive integer(s)')
        if len(shape) > MAX_NDIM:
            raise ValueError('max number of dimension is {}'.format(MAX_NDIM))
        return True

    def reshape(self, shape: Tuple[int, ...]) -> BinaryWaveHeader5:
        if not self.__is_valid_shape(shape):
            raise ValueError('invalid shape')
        if reduce(lambda x, y: x * y, shape) != self.__npnts:
            raise ValueError('new shape does not match to original number '
                             'of data points ({} points)'.format(self.__npnts))
        self.__shape = shape

        # following informations will initialized
        self.__axes_unit = DEFAULT_AXES_UNIT
        self.__axes_start = DEFAULT_AXES_START
        self.__axes_delta = DEFAULT_AXES_DELTA
        self.__axes_label_size = DEFAULT_AXES_LABEL_SIZE

        return self

    @property
    def ndim(self) -> int:
        return len(self.__shape)

    @property
    def dtype(self) -> str:
        return self.__dtype

    def is_valid_dtype(self, dtype: str) -> bool:
        if not isinstance(dtype, str):
            raise TypeError('data type must be passed as string')
        if dtype not in VALID_DTYPES:
            raise TypeError('invalid data type')
        return True

    def set_dtype(self, dtype: str) -> BinaryWaveHeader5:
        if not self.is_valid_dtype(dtype):
            raise TypeError('invalid data type')
        self.__dtype = dtype
        return self

    @property
    def data_unit(self) -> Union[str, None]:
        res = self.__data_unit if isinstance(self.__data_unit, str) else None
        return res

    def set_data_unit(self, unit: str) -> BinaryWaveHeader5:
        self.__data_unit = len(unit) if len(unit) > 3 else unit
        return self

    @property
    def axes_unit(self) -> List[Union[str, None]]:
        res = [unit if isinstance(unit, str) else None
               for unit in self.__axes_unit]
        return res

    def __is_valid_axis_index(self, axis_index: int) -> bool:
        if not isinstance(axis_index, int):
            raise TypeError('axis_index must be passed as an integer')
        if not 0 <= axis_index < self.ndim:
            raise KeyError('this wave has only {} dimensions'.format(self.ndim))
        return True

    def set_axis_unit(self, axis_index: int, unit: str) -> BinaryWaveHeader5:
        if not self.__is_valid_axis_index(axis_index):
            raise ValueError('invalid axis_index')
        units = list(self.__axes_unit)
        units[axis_index] = len(unit) if len(unit) > 3 else unit
        res = cast(Tuple[Union[str, int], Union[str, int],
                         Union[str, int], Union[str, int]], tuple(units))
        self.__axes_unit = res
        return self

    def calculated_axis_wave(self, axis_index: int) -> np.ndarray:
        if not self.__is_valid_axis_index(axis_index):
            raise ValueError('invalid axis_index')
        size = self.shape[axis_index]
        start = self.__axes_start[axis_index]
        step = self.__axes_delta[axis_index]

        res = np.full(size, start)
        increments = np.arange(size) * step

        res += increments
        return res

    def set_axis_scale(self, axis_index: int,
                       start: float, delta: float) -> BinaryWaveHeader5:
        if not self.__is_valid_axis_index(axis_index):
            raise ValueError('invalid axis_index')
        if not (isinstance(start, float) and isinstance(delta, float)):
            raise TypeError('invalid argument type')
        starts = list(self.__axes_start)
        deltas = list(self.__axes_delta)

        starts[axis_index] = start
        deltas[axis_index] = delta

        res_starts = cast(Tuple[float, float, float, float], tuple(starts))
        res_deltas = cast(Tuple[float, float, float, float], tuple(deltas))

        self.__axes_start = res_starts
        self.__axes_delta = res_deltas
        return self

    def initialize_axis_label_size(self) -> BinaryWaveHeader5:
        self.__axes_label_size = DEFAULT_AXES_LABEL_SIZE
        return self

    @property
    def data_scale(self) -> Union[Tuple[float, float], None]:
        return self.__data_scale

    def set_data_scale(self, max_: float, min_: float) -> BinaryWaveHeader5:
        if not (isinstance(max_, float) and isinstance(min_, float)):
            raise TypeError('invalid argument type')
        self.__data_scale = (max_, min_)
        return self

    def __datetime_to_num(self, time: datetime.datetime) -> int:
        res = time - DATETIME_OFFSET
        return int(res.total_seconds())

    @property
    def creation_time(self) -> datetime.datetime:
        return self.__creation_time

    def set_creation_time(self, time: datetime.datetime) -> BinaryWaveHeader5:
        self.__creation_time = time
        return self

    def update_creation_time(self) -> BinaryWaveHeader5:
        self.__creation_time = datetime.datetime.now()
        return self

    @property
    def modify_time(self) -> datetime.datetime:
        return self.__modify_time

    def initialize_modify_time(self) -> BinaryWaveHeader5:
        self.__modify_time = DATETIME_OFFSET
        return self

    def update_modify_time(self) -> BinaryWaveHeader5:
        self.__modify_time = datetime.datetime.now()
        return self

    @property
    def __npnts(self) -> int:
        return reduce(lambda x, y: x * y, self.__shape)

    @property
    def __type_size(self) -> int:
        return DTYPE_BYTES[self.__dtype]

    @property
    def __ex_data_unit_size(self) -> int:
        res = self.__data_unit if isinstance(self.__data_unit, int) else 0
        return res

    @property
    def __ex_axes_unit_size(self) -> Tuple[int, int, int, int]:
        res = tuple(unit if isinstance(unit, int) else 0
                    for unit in self.__axes_unit)
        res = cast(Tuple[int, int, int, int], res)
        return res

    @property
    def section_sizes(self) -> __SectionSizes:
        value_size = self.__npnts * self.__type_size

        res: __SectionSizes = {
            'value_size': value_size,
            'formula_size': self.formula_size,
            'note_size': self.note_size,
            'ex_data_unit_size': self.__ex_data_unit_size,
            'ex_axes_unit_size': self.__ex_axes_unit_size,
            'axes_label_size': self.__axes_label_size}

        return res

    @property
    def buffer(self) -> bytes:
        binary_header_buf = self.__binary_header_buffer()
        wave_header_buf = self.__wave_header_buffer()

        header_buf = bytearray(binary_header_buf + wave_header_buf)
        checksum = int(self.__checksum(header_buf) * (-1))
        checksum_buf = checksum.to_bytes(2, byteorder='little', signed=True)
        header_buf[2:4] = checksum_buf

        return bytes(header_buf)

    def __binary_header_buffer(self) -> bytes:
        version = 5
        checksum = 0  # temporal value
        wfm_size = WAVE_HEADER_SIZE + self.__type_size * self.__npnts
        formula_size = self.formula_size
        note_size = self.note_size
        data_eunits_size = self.__ex_data_unit_size
        dim_eunits_size = self.__ex_axes_unit_size
        dim_elabels_size = self.__axes_label_size
        s_indices_size = 0  # used in text wave
        options_size_1 = 0  # reserved
        options_size_2 = 0  # reserved

        values = (
            version, checksum, wfm_size,
            formula_size, note_size,
            data_eunits_size, *dim_eunits_size, *dim_elabels_size,
            s_indices_size, options_size_1, options_size_2)
        res = struct.pack('2h15i', *values)

        return res

    def __wave_header_buffer(self) -> bytes:
        next_ = 0  # pointer (no meaning in python)
        creation_time = self.__datetime_to_num(self.__creation_time)
        mod_time = self.__datetime_to_num(self.__modify_time)
        npnts = self.__npnts
        type_ = DTYPE_IDS[self.__dtype]
        d_lock = 0  # reserved

        values_1 = (
            next_, creation_time, mod_time,
            npnts, type_, d_lock)
        buffer_1 = struct.pack("iIIihh", *values_1)

        whpad1 = bytes('', encoding=TEXT_ENCODE)  # reserved
        wh_version = 1
        name = bytes(self.__name, encoding=TEXT_ENCODE)
        whpad2 = 0  # reserved
        data_folder = 0  # pointer (no meaning in python)

        values_2 = (
            whpad1, wh_version, name, whpad2, data_folder)
        buffer_2 = struct.pack("6sh32sii", *values_2)

        n_dim = [0, 0, 0, 0]
        for index, size in enumerate(self.__shape):
            n_dim[index] = size
        sf_a = self.__axes_delta
        sf_b = self.__axes_start

        values_3 = (
            *n_dim, *sf_a, *sf_b)
        buffer_3 = struct.pack("4i4d4d", *values_3)

        data_unit = bytes(self.data_unit if self.data_unit else '',
                          encoding=TEXT_ENCODE)
        dim_units = [bytes(unit if unit else '', encoding=TEXT_ENCODE)
                     for unit in self.axes_unit]
        if self.data_scale:
            fs_valid = 1
            top_full_scale = self.data_scale[0]
            bot_full_scale = self.data_scale[1]
        else:
            fs_valid = 0
            top_full_scale = 0
            bot_full_scale = 0
        whpad3 = 0  # reserved

        values_4 = (
            data_unit, *dim_units, fs_valid, whpad3,
            top_full_scale, bot_full_scale)
        buffer_4 = struct.pack("4s4s4s4s4shhdd", *values_4)

        values_5 = tuple(0 for i in range(26))  # pointers and reserved
        buffer_5 = struct.pack("i4i4ii16i", *values_5)

        values_6 = tuple(0 for i in range(11))  # private to igor
        buffer_6 = struct.pack("hhh??iihhii", *values_6)  # format: hhhcciihhii

        res = buffer_1 + buffer_2 + buffer_3 + buffer_4 + buffer_5 + buffer_6
        return res

    def __checksum(self, buffer: bytes) -> int:
        values = np.array(struct.unpack("192h", buffer))
        checksum = np.sum(values, dtype=np.int16)
        return checksum


class BinaryWaveHeader5Loader:
    def __init__(self) -> None:
        pass

    def load_from_buffer(self, bin_header: bytes,
                         wave_header: bytes) -> BinaryWaveHeader5:
        version = struct.unpack("h", bin_header[0:2])[0]
        if version != 5:
            if version == 7:
                print('Warning: Got version 7 Igor binary wave file. '
                      'Long wave name and/or long dimension labels '
                      'will ignored.')
            else:
                raise TypeError(
                    'only version 5 Igor binary wave files '
                    'are supported (got version {})'.format(version))

        binh_values = self.__unpack_binary_header(bin_header)
        waveh_values = self.__unpack_wave_header(wave_header)

        name = waveh_values['name']
        if name == ':wave name too long:':
            name = DEFAULT_WAVE_NAME
            print('Warning: Long wave name is not supported. '
                  'Wave name is set to default ({}).'.format(name))

        data_unit_size = binh_values['data_unit_size']
        data_unit_str = waveh_values['data_unit']
        data_unit = data_unit_size if data_unit_size != 0 else data_unit_str
        data_unit = cast(Union[str, int], data_unit)

        axes_unit_size = binh_values['axes_unit_size']
        axes_unit_str = waveh_values['axes_unit']
        axes_unit = tuple(axis_unit_size if axis_unit_size != 0 else axis_unit
                          for axis_unit_size, axis_unit
                          in zip(axes_unit_size, axes_unit_str))
        axes_unit = cast(Tuple[Union[str, int], Union[str, int],
                               Union[str, int], Union[str, int]],
                         axes_unit)

        header = BinaryWaveHeader5(
            shape=waveh_values['shape'], name=name,
            dtype=waveh_values['dtype'],
            formula_size=binh_values['formula_size'],
            note_size=binh_values['note_size'],
            data_unit=data_unit, axes_unit=axes_unit,
            axes_start=waveh_values['axes_start'],
            axes_delta=waveh_values['axes_delta'],
            axes_label_size=binh_values['axes_label_size'],
            creation_time=waveh_values['creation_datetime'],
            modify_time=waveh_values['mod_datetime'],
            data_scale=waveh_values['data_scale']
        )

        return header

    def __unpack_binary_header(self, bin_header: bytes) -> __BinaryHeaderValues:
        # 64 bytes
        values = struct.unpack("2h15i", bin_header)

        # size of the dependency formula, if any.
        formula_size = cast(int, values[3])
        note_size = cast(int, values[4])  # size of the note text
        # size of optional extended data unit
        data_unit_size = cast(int, values[5])
        # sizes of optional extended dimension units
        axes_unit_size = cast(Tuple[int, int, int, int], values[6:10])
        # sizes of optional dimension labels
        axes_label_size = cast(Tuple[int, int, int, int], values[10:14])

        # size of string indicies if text wave
        string_indice_size = cast(int, values[14])
        is_text_wave = string_indice_size != 0
        if is_text_wave:
            raise TypeError('text wave is not supported')

        res: __BinaryHeaderValues = {
            'formula_size': formula_size,
            'note_size': note_size,
            'data_unit_size': data_unit_size,
            'axes_unit_size': axes_unit_size,
            'axes_label_size': axes_label_size}

        return res

    def __unpack_wave_header(self, wave_header: bytes) -> __WaveHeaderValues:

        # 1st section (20 bytes)
        header_1 = wave_header[0:20]
        values_1 = struct.unpack("iIIihh", header_1)
        creation_datetime = self.__num_to_datetime(
            values_1[1])  # datetime of creation
        # datetime of last modification
        mod_datetime = self.__num_to_datetime(values_1[2])
        npnts = values_1[3]  # total number of points
        dtype = cast(DTypes, WAVETYPES[values_1[4]])  # data type of wave
        if dtype in ('text', 'complex', 'unsigned'):
            raise TypeError('{} wave is not supported'.format(dtype))

        # 2nd section (48 bytes)
        header_2 = wave_header[20:68]
        values_2 = struct.unpack("6sh32sii", header_2)
        name = cast(str, decode_unicode(values_2[2].split(b'\x00', 1)[0]))

        # 3rd section (80 bytes)
        header_3 = wave_header[68:148]
        values_3 = struct.unpack("4i4d4d", header_3)
        shape = cast(
            Tuple[int, ...], tuple(size for size in values_3[0:4] if size != 0))
        points_num = reduce(lambda x, y: x * y, shape)
        if not points_num == npnts:
            raise ValueError(
                'number of points (npnts) does not match with shape')
        axes_delta = cast(Tuple[float, float, float, float], values_3[4:8])
        axes_start = cast(Tuple[float, float, float, float], values_3[8:12])

        # 4th section (40 bytes)
        header_4 = wave_header[148:188]
        values_4 = struct.unpack("4s4s4s4s4shhdd", header_4)
        data_unit = cast(str, decode_unicode(values_4[0].split(b'\x00', 1)[0]))
        axes_unit = cast(Tuple[str, str, str, str],
                         tuple([decode_unicode(unit.split(b'\x00', 1)[0])
                                for unit in values_4[1:5]]))
        has_data_scale = bool(values_4[5])

        if has_data_scale:
            data_scale = cast(Union[Tuple[float, float], None],
                              (values_4[7], values_4[8]))
        else:
            data_scale = None

        # skip following headers (104 + 28 bytes)
        # format: i4i4ii16i, hhhcciihhii

        res: __WaveHeaderValues = {
            'creation_datetime': creation_datetime,
            'mod_datetime': mod_datetime,
            'dtype': dtype,
            'name': name,
            'shape': shape,
            'axes_delta': axes_delta,
            'axes_start': axes_start,
            'data_unit': data_unit,
            'axes_unit': axes_unit,
            'data_scale': data_scale}
        return res

    def __num_to_datetime(self, num: int) -> datetime.datetime:
        return DATETIME_OFFSET + datetime.timedelta(seconds=num)


class __BinaryHeaderValues(TypedDict):
    formula_size: int
    note_size: int
    data_unit_size: int
    axes_unit_size: Tuple[int, int, int, int]
    axes_label_size: Tuple[int, int, int, int]


class __WaveHeaderValues(TypedDict):
    creation_datetime: datetime.datetime
    mod_datetime: datetime.datetime
    dtype: DTypes
    name: str
    shape: Tuple[int, ...]
    axes_delta: Tuple[float, float, float, float]
    axes_start: Tuple[float, float, float, float]
    data_unit: str
    axes_unit: Tuple[str, str, str, str]
    data_scale: Union[Tuple[float, float], None]


class __SectionSizes(TypedDict):
    value_size: int
    formula_size: int
    note_size: int
    ex_data_unit_size: int
    ex_axes_unit_size: Tuple[int, int, int, int]
    axes_label_size: Tuple[int, int, int, int]
