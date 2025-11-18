from enum import Enum
from typing import Self


class ValueTag(Enum):
    Root = 0
    Variable = 1
    BaseType = 2
    Pointer = 3
    Array = 4
    Struct = 5
    Enum = 6
    EnumValue = 7
    Typedef = 8


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

    def debug_print(self):
        skip = set()

        def debug(value: Value, parents: set[Value]):
            show_kids = True
            text = f"{str(value.tag).split('.')[-1]}({value.name!r},{value.value!r})"
            if text == "":
                text = str(value.tag)
            if value in parents:
                text += " (CYCLE)"
                show_kids = False
            if value in skip:
                text += " (REUSED)"
                show_kids = False
            else:
                skip.add(value)
            print(f"{"    "*len(parents)}{text}")
            if show_kids:
                for c in value.children:
                    debug(c, parents + [value])

        debug(self, [])

    def equals_deep(self, other: Self) -> bool:
        def values_are_equal(left: Self, right: Value, left_parents: list[Value], right_parents: list[Value]) -> bool:
            """Compare if two values match exactly by deep comparison"""
            if left == right:
                return True

            if left.tag != right.tag:
                return False

            if left.name != right.name:
                return False

            if left.value != right.value:
                return False

            if len(left.children) != len(right.children):
                return False

            # There is a cycle
            left_cycle = left in left_parents
            right_cycle = right in right_parents
            if left_cycle and right_cycle:
                return left_parents.index(left) == right_parents.index(right)

            # Non matching cycles
            if left_cycle or right_cycle:
                return False

            left_parents = left_parents + [left]
            right_parents = right_parents + [right]
            for left_child, right_child in zip(left.children, right.children):
                if not values_are_equal(left_child, right_child, left_parents, right_parents):
                    return False
            return True

        return values_are_equal(self, other, [], [])

    def deduplicate(self):
        """Deduplicate equal values in the tree"""

        visited: dict[(ValueTag, str, int, int), set[Value]] = dict()
        cache: dict[Value, Value] = dict()

        def visit(value: Value) -> Value:
            if value in cache:
                return cache[value]

            key = (value.tag, value.name, value.value, len(value.children))
            vis = visited.setdefault(key, set())

            # Compre deeply
            for v in vis:
                if v.equals_deep(value):
                    cache[value] = v
                    return v

            cache[value] = value
            vis.add(value)
            value.children = [visit(c) for c in value.children]
            return value

        visit(self)


def test_dedup0():
    value = Value(ValueTag.Root, "root")
    value.deduplicate()
    assert value.name == "root"
    assert value.children == []


def test_dedup_do_nothing():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.Variable, "CU0")
    cu1 = Value(ValueTag.Variable, "CU1")

    # Distinct
    value.children = [cu0, cu1]
    value.deduplicate()
    assert value.children == [cu0, cu1]
    assert cu0.children == []
    assert cu1.children == []
    assert value.name == "root"


def test_dedup1():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.Variable, "CU0")
    cu1 = Value(ValueTag.Variable, "CU1")
    cu2 = Value(ValueTag.Variable, "CU0")
    cu3 = Value(ValueTag.Variable, "CU1")
    cu4 = Value(ValueTag.Variable, "CU4")
    cu5 = Value(ValueTag.Variable, "CU0")

    value.children = [cu0, cu1, cu2, cu3, cu4, cu5]
    value.deduplicate()
    assert value.children == [cu0, cu1, cu0, cu1, cu4, cu0]


def test_dedup2():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.Variable, "CU0")
    cu1 = Value(ValueTag.Variable, "CU1")
    cu2 = Value(ValueTag.Variable, "CU0")

    var1 = Value(ValueTag.BaseType, "int1", 1)
    var2 = Value(ValueTag.BaseType, "int2", 2)
    var3 = Value(ValueTag.BaseType, "int3", 3)
    var4 = Value(ValueTag.BaseType, "int4", 4)

    cu0.children = [var1, var2, var3, var4]
    cu1.children = [var1, var2, var3, var4]
    cu2.children = [var1, var2, var3, var4]
    value.children = [cu0, cu1, cu2]
    value.deduplicate()
    assert value.children == [cu0, cu1, cu0]


def test_dedup3():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.Variable, "CU0")
    cu1 = Value(ValueTag.Variable, "CU0")
    cu2 = Value(ValueTag.Variable, "CU0")

    var1 = Value(ValueTag.BaseType, "int1", 1)
    var2 = Value(ValueTag.BaseType, "int1", 2)
    var3 = Value(ValueTag.BaseType, "int1", 3)
    var4 = Value(ValueTag.BaseType, "int1", 4)

    cu0.children = [var1, var2, var3, var4]
    cu1.children = [var1, var2, var3, var4]
    cu2.children = [var1, var2, var3, var4]
    value.children = [cu0, cu1, cu2]
    value.deduplicate()
    assert value.children == [cu0, cu0, cu0]
    assert cu0.children == [var1, var2, var3, var4]


def test_dedup4():
    value = Value(ValueTag.Root, "root")
    cu0 = Value(ValueTag.Variable, "CU0")
    cu1 = Value(ValueTag.Variable, "CU0")
    cu2 = Value(ValueTag.Variable, "CU0")

    var1 = Value(ValueTag.BaseType, "int1", 1)
    var2 = Value(ValueTag.BaseType, "int1", 1)
    var3 = Value(ValueTag.BaseType, "int1", 1)
    var4 = Value(ValueTag.BaseType, "int1", 1)

    cu0.children = [var1, var2, var3, var4]
    cu1.children = [var1, var2, var3, var4]
    cu2.children = [var1, var2, var3, var4]
    value.children = [cu0, cu1, cu2]
    value.deduplicate()
    assert value.children == [cu0, cu0, cu0]
    assert cu0.children == [var1, var1, var1, var1]


def test_dedup5():
    root = Value(ValueTag.Root, "Root")
    cu0 = Value(ValueTag.Variable, "CU0")
    cu1 = Value(ValueTag.Variable, "CU1")
    cu2 = Value(ValueTag.Variable, "CU1")
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

    root.deduplicate()
    assert root.children == [cu0, cu1, cu1]
    assert cu0.children == [var_x0, var_y0, var_x0, var_y2]
    assert cu1.children == [var_x0, var_y0, var_x0, var_y2]
