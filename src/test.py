from value import Value, ValueTag, deduplicate
from store import encode, decode
from dwarfdb import load
import zlib

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
data_normal = encode(root)
deduplicate(root)
data_dedup = encode(root)

print(f"normal:      {len(data_normal) // 1024}")
print(f"dedup:       {len(data_dedup) // 1024}")
print(f"normal zlib: {len(zlib.compress(data_normal)) // 1024}")
print(f"dedup  zlib: {len(zlib.compress(data_dedup)) // 1024}")
