from enum import Enum
from typing import Self


class ValueTag(Enum):
    Root = 0
    CompileUnit = 1
    Variable = 2
    BaseType = 3
    Pointer = 4
    Array = 5
    Struct = 6
    Enum = 7
    EnumValue = 8
    Typedef = 9


class Value:
    def __init__(self, tag: ValueTag, name: str, value: int = 0):
        # What kind of value is this?
        # base_type, variable, ... etc
        self.tag = tag

        # Value name (Can be empty)
        self.name = name

        # Argument, depends on value tag:
        #   Array:     Number of elements
        #   Variable:  Offset from the base
        #   EnumValue: Value of this enum variant  enum value
        self.value = value

        # Child nodes, struct members, enum values
        self.children: list[Self] = []

    def type(self) -> Self:
        if self.tag in [ValueTag.Variable, ValueTag.Pointer, ValueTag.Array, ValueTag.Typedef]:
            return self.children[0]
        return None

    def bottom(self) -> Self:
        """Get bottom most type"""
        if self.type() is not None:
            return self.type().bottom()
        return self

    def untypedef(self) -> Self:
        """Get bottom most type"""
        if self.tag in [ValueTag.Typedef]:
            return self.type().untypedef()
        return self

    def pretty(self) -> str:
        if self.tag == ValueTag.Root:
            return f"Root {self.name}"
        if self.tag == ValueTag.CompileUnit:
            return f"CompileUnit {self.name}"
        if self.tag == ValueTag.Variable:
            return f"{self.type().pretty()} {self.name}"
        if self.tag == ValueTag.BaseType:
            return self.name
        if self.tag == ValueTag.Pointer:
            return f"{self.type().pretty()}*"
        if self.tag == ValueTag.Array:
            return f"{self.type().pretty()}[{self.value}]"
        if self.tag == ValueTag.Struct:
            return f"struct {self.name}"
        if self.tag == ValueTag.Enum:
            return f"enum {self.name}"
        if self.tag == ValueTag.EnumValue:
            return f"{self.name} = {self.value}"
        if self.tag == ValueTag.Typedef:
            return self.name
        return None

    def variables(self) -> list[Self]:
        if self.tag == ValueTag.Root:
            return set(v for c in self.children for v in c.variables())

        if self.tag == ValueTag.CompileUnit:
            return self.children

        return []

    def find_variable(self, name: str) -> Self:
        for v in self.variables():
            if v.name == name:
                return v
        return None


def value_contents(value: Value) -> tuple:
    # print(f"value_contents {value.tag} {value.name}")
    visited: set[Value] = set()

    def contents_simple(val: Value) -> tuple:
        return (val.tag, val.name, val.value, len(val.children))

    def contents_full(val: Value) -> tuple:
        # print(f"  {val.tag} {val.name}")
        # Cycle detected, not possible
        if val in visited:
            print("cycle")
            return None

        visited.add(val)

        children = []
        for c in val.children:
            child_cont = contents_full(c)

            # Cycle detected, skip this
            if child_cont is None:
                return None

            children.append(child_cont)
        return (contents_simple(val), tuple(children))

    return contents_full(value)


def deduplicate(value: Value):
    # Full tree to value mapping
    dedup_table: dict[tuple, Value] = dict()
    value_table: dict[Value, Value] = dict()

    def dedup_one(value: Value):
        if value in value_table:
            return value_table[value]

        cont = value_contents(value)

        if cont is None:
            value_table[value] = value
        elif cont in dedup_table:
            old_value = value
            value = dedup_table[cont]
            value_table[old_value] = value
        else:
            value_table[value] = value
            dedup_table[cont] = value

        value.children = [dedup_one(c) for c in value.children]
        return value

    dedup_one(value)


def test_dedup0():
    value = Value(ValueTag.Root, "root")
    deduplicate(value)
    assert value.name == "root"
    assert value.children == []


def test_dedup_do_nothing():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.CompileUnit, "CU0")
    cu1 = Value(ValueTag.CompileUnit, "CU1")

    # Distinct
    value.children = [cu0, cu1]
    deduplicate(value)
    assert value.children == [cu0, cu1]
    assert cu0.children == []
    assert cu1.children == []
    assert value.name == "root"


def test_dedup1():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.CompileUnit, "CU0")
    cu1 = Value(ValueTag.CompileUnit, "CU1")
    cu2 = Value(ValueTag.CompileUnit, "CU0")
    cu3 = Value(ValueTag.CompileUnit, "CU1")
    cu4 = Value(ValueTag.CompileUnit, "CU4")
    cu5 = Value(ValueTag.CompileUnit, "CU0")

    value.children = [cu0, cu1, cu2, cu3, cu4, cu5]
    deduplicate(value)
    assert value.children == [cu0, cu1, cu0, cu1, cu4, cu0]


def test_dedup2():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.CompileUnit, "CU0")
    cu1 = Value(ValueTag.CompileUnit, "CU1")
    cu2 = Value(ValueTag.CompileUnit, "CU0")

    var1 = Value(ValueTag.BaseType, "int1", 1)
    var2 = Value(ValueTag.BaseType, "int2", 2)
    var3 = Value(ValueTag.BaseType, "int3", 3)
    var4 = Value(ValueTag.BaseType, "int4", 4)

    cu0.children = [var1, var2, var3, var4]
    cu1.children = [var1, var2, var3, var4]
    cu2.children = [var1, var2, var3, var4]
    value.children = [cu0, cu1, cu2]
    deduplicate(value)
    assert value.children == [cu0, cu1, cu0]


def value():
    root = Value(ValueTag.Root, "Root")
    cu0 = Value(ValueTag.CompileUnit, "CU0")
    cu1 = Value(ValueTag.CompileUnit, "CU1")
    cu2 = Value(ValueTag.CompileUnit, "CU1")
    root.children = [cu0, cu1, cu2]

    type_int = Value(ValueTag.BaseType, "int", 4)
    type_char = Value(ValueTag.BaseType, "char", 1)

    var_x0 = Value(ValueTag.Variable, "x")
    var_x0.children = [type_int]

    var_x1 = Value(ValueTag.Variable, "x")
    var_x1.children = [type_int]

    var_x2 = Value(ValueTag.Variable, "x")
    var_x2.children = [type_int]

    var_y0 = Value(ValueTag.Variable, "y")
    var_y0.children = [type_char]

    var_y1 = Value(ValueTag.Variable, "y")
    var_y1.children = [type_char]

    var_y2 = Value(ValueTag.Variable, "y")
    var_y2.children = [type_int]

    cu0.children = [var_x0, var_y0, var_x2, var_y2]
    cu1.children = [var_x1, var_y1, var_x2, var_y2]
    cu2.children = [var_x0, var_y0, var_x2, var_y2]

    deduplicate(root)
    assert root.children == [cu0, cu1, cu0]
    assert cu0.children == [var_x0, var_y0, var_x0, var_y2]
    assert cu1.children == [var_x0, var_y0, var_x0, var_y2]
