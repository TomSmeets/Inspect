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
    def __init__(self, tag:ValueTag, name: str, value: int = 0):
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
        if self.tag in [ ValueTag.Variable, ValueTag.Pointer, ValueTag.Array, ValueTag.Typedef ]:
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

def deduplicate(value: Value) -> Value:
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
    return dedup_one(value)
