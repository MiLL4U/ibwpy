import ibwpy as ip
import numpy as np

PATH = "testwave.ibw"

wave = ip.load(PATH)
print(wave.shape)
wave[:, :, 1:2, :] = 3.1415
print(wave)
wave.save("testwave_2.ibw")

print(wave.name)
print(wave.shape)
print(wave.array)
print(wave.modify_time)

print(wave.data_unit)
wave.set_data_unit('kg')
print(wave.data_unit)

print(wave.axes_unit)
wave.set_axis_unit(1, 'count')
wave.set_axis_unit(axis_index=2, unit='hPa')
print(wave.axes_unit)

print(wave.calculated_axis_wave(1))
wave.set_axis_scale(1, 10, -0.1)
print(wave.calculated_axis_wave(1))

print(wave.data_scale)
wave.set_data_scale(100, 0)
print(wave.data_scale)

note = wave.note.replace('\r', '\r\n')
print(note)
wave.set_note("Lorem ipsum dolor sit amet.\n This is test note.")
print(wave.note)

print(wave.creation_time)
print(wave.modify_time)

wave.reshape([6, 20])
print(wave)
print()

new_wave = ip.make([4, 3], 'NewWave')
new_wave.rename('RenamedWave')
new_wave.set_values(3)
print(new_wave)
new_wave.set_values(np.array([[1, 0, 1],
                              [0, 1, 0],
                              [1, 0, 1],
                              [0, 1, 0]]))
new_wave.save("testwave_2.ibw")
added = new_wave + 1 + [1, 2, 3] + [0.2, 0.4, 0.6] \
        + new_wave * np.array([2.3, 0, 3])
print(added)
added = new_wave.__add__(1)
print(new_wave.name)
print(new_wave)
print(new_wave[2])
print(new_wave[2][0])

duplicated_wave = new_wave.duplicate("duplicated")
new_wave[2][1] = 25
print(new_wave)
print(duplicated_wave)
print()

nparr = np.array([[1, 2, 3],
                  [4.2, 4.4, 4.6],
                  [5.2, 5.4, 5.6],
                  [6.2, 6.4, 6.6]], dtype='float64')
fromnp = ip.from_nparray(nparr, 'wave_from_np')
print(fromnp)

add_test = added + fromnp
print(add_test)

test_wave = ip.make([2, 3, 5], "test", dtype='float64')
test_wave[0][1] = [1, 2, 3, 4, 5]
test_wave[1][2] = 4
test_wave[0][0] = np.random.rand(5)
print(test_wave)
test_wave_added = test_wave + 1
test_wave.save('testwave_3.ibw')
