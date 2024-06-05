import re

import numpy as np

import ibwpy as ip

test_arr = np.array([
    [0.0, 0.1, 0.2],
    [0.1, 0.2, 0.3],
    [0.2, 0.3, 0.4]
], dtype=np.float32)

# eng = ip.from_nparray(test_arr, "eng")
# eng.set_note("The quick brown fox jumps over the lazy dog.")

jp = ip.from_nparray(test_arr, "jp")
jp.set_note("生物構造化学分野\nThe quick brown fox jumps over the lazy dog.")

# print(eng)
# eng.save()

print(jp.array)
jp.save()

jp_igor = ip.load("./buffer_01.ibw")
print(jp_igor.array)
note = re.sub(r'\r\n|\r|\n', r'\n', jp_igor.note)
print(note)
print()
jp_igor.save("./buffer_01_resave.ibw")
