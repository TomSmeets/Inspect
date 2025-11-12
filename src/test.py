from value import Value, ValueTag,deduplicate
from store import encode,decode
from dwarfdb import load

root = Value(ValueTag.Root, "Root")

cu0 = Value(ValueTag.CompileUnit, "CU0")
cu1 = Value(ValueTag.CompileUnit, "CU1")
root.children = [ cu0, cu1 ]

type_int  = Value(ValueTag.BaseType, "int",  4)
type_char = Value(ValueTag.BaseType, "char", 1)

var_x0 = Value(ValueTag.Variable, "x")
var_x0.children = [ type_int ]

var_x1 = Value(ValueTag.Variable, "x")
var_x1.children = [ type_int ]

var_y0 = Value(ValueTag.Variable, "y")
var_y0.children = [ type_char ]

var_y1 = Value(ValueTag.Variable, "y")
var_y1.children = [ type_char ]

cu0.children = [ var_x0, var_y0 ]
cu1.children = [ var_x1, var_y1 ]

print(root.pretty())
print(cu0.pretty())
print(cu1.pretty())

for cu in root.children:
    print(cu.pretty())
    for var in cu.children:
        print(" ", var.pretty())

print("Variables: ")
for var in root.variables():
    print(var.pretty())

print("Dedup")
root = deduplicate(root)
    
print("Variables: ")
for var in root.variables():
    print(var.pretty())

root_2 = decode(encode(root))
# print("DEDUPE2")
# deduplicate(root)

print("Root2")
for cu in root_2.children:
    print(cu.pretty())
    for var in cu.children:
        print(" ", var.pretty())
root = load("main.elf")
