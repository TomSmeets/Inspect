from value import Value, ValueTag, deduplicate
from store import encode, decode
from dwarfdb import load
import zlib

import time

root = Value(ValueTag.Root, "Root")

cu0 = Value(ValueTag.CompileUnit, "CU0")
cu1 = Value(ValueTag.CompileUnit, "CU1")
root.children = [cu0, cu1]

type_int = Value(ValueTag.BaseType, "int", 4)
type_char = Value(ValueTag.BaseType, "char", 1)

var_x0 = Value(ValueTag.Variable, "x")
var_x0.children = [type_int]

var_x1 = Value(ValueTag.Variable, "x")
var_x1.children = [type_int]

var_y0 = Value(ValueTag.Variable, "y")
var_y0.children = [type_char]

var_y1 = Value(ValueTag.Variable, "y")
var_y1.children = [type_char]

cu0.children = [var_x0, var_y0]
cu1.children = [var_x1, var_y1]

root = load("main.elf")
data_normal        = encode(root)
data_normal_old    = encode(root, stripe=False)

start = time.time()
deduplicate(root)
end = time.time()
print(f"Duration:        {int((end - start)*1000):>8} ms")
data_dedup = encode(root)
data_dedup_old    = encode(root, stripe=False)

print(f"normal_old:      {len(data_normal_old):>8}")
print(f"normal:          {len(data_normal):>8}")
print(f"dedup_old:       {len(data_dedup_old):>8}")
print(f"dedup:           {len(data_dedup):>8}")
print(f"normal zlib old: {len(zlib.compress(data_normal_old)):>8}")
print(f"normal zlib:     {len(zlib.compress(data_normal)):>8}")
print(f"dedup  zlib old: {len(zlib.compress(data_dedup_old)):>8}")
print(f"dedup  zlib:     {len(zlib.compress(data_dedup)):>8}")
