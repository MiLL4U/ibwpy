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
jp.set_note("生物構造化学分野")

# print(eng)
# eng.save()

print(jp.array)
jp.save()

jp_igor = ip.load("./jp_igor.ibw")
print(jp_igor.array)
print(jp_igor.note)
print()
