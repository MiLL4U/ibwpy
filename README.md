# ibwpy
Read and write Igor binary wave with Python

## Installation
1. Clone this repository

```bash
$ git clone https://github.com/MiLL4U/ibwpy.git
```

2. Go into the repository

```bash
$ cd ibwpy
```

3. Install ibwpy with setup.py

```bash
$ python setup.py install
```

## Examples
### Read
Read wave from ibw file:
```python
test_wave = ip.load("test_wave.ibw")
print(test_wave)
```

### Make
Make new wave from Numpy array
```python
import numpy as np

arr_1 = np.array([[1., 2., 3.],
                  [1.5, 2.5, 3.5]])
wave_1 = ip.from_nparray(arr_1, 'wave1')
# wave1 (IgorBinaryWave)
# [[1.  2.  3. ]
#  [1.5 2.5 3.5]]
```

### Calculation
Treat wave as NumPy array:
```python
arr_2 = np.ones((2, 3))
print(arr_2)
# [[1. 1. 1.]
#  [1. 1. 1.]]

wave_1 = wave_1 + arr_2
print(wave_1)
# wave1 (IgorBinaryWave)
# [[2.  3.  4. ]
#  [2.5 3.5 4.5]]
```

### Save
Save wave as ibw file
```python
wave_1.save("wave1.ibw")
```