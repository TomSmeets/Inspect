import struct
from enum import Enum
from typing import Self
from io import BytesIO

# Database format version
STORE_VERSION: int = 1


# How to encode 'None' for Value.type
VALUE_ID_NONE: int = 0xFFFFFFFF

# How to encode 'None' for Valye.value
VALUE_VALUE_NONE: int = 0xFFFFFFFFFFFFFFFF


# Encode / decode table of enums
class ValueTag(Enum):
    CompileUnit = 0
    Function = 1
    Variable = 2
    BaseType = 3
    Pointer = 4
    Array = 5
    Struct = 6
    Enum = 7
    EnumValue = 8
    Typedef = 9


class Value:
    def __init__(self):
        # Uniqe id and index into the values array
        self.id: int = 0

        # What kind of value is this?
        # base_type, variable, ... etc
        self.tag: ValueTag = None

        # Value name (Can be empty)
        self.name: str = ""

        # Argument, depends on value tag:
        #   Array:     Number of elements
        #   Variable:  Offset from the base
        #   EnumValue: Value of this enum variant  enum value
        self.value: int = 0

        # Type of variable, or inner type of another type
        self.type = None

        # Child nodes, struct members, enum values
        self.children = []

    def bottom(self) -> Self:
        """Get bottom most type"""
        if self.type is not None:
            return self.type.bottom()
        return self

    def untypedef(self) -> Self:
        """Get bottom most type"""
        if self.tag in [ValueTag.Typedef]:
            return self.type.untypedef()
        return self

    def pretty(self) -> str:
        if self.tag == ValueTag.CompileUnit:
            return f"CompileUnit {self.name}"
        if self.tag == ValueTag.Function:
            return f"{self.type.pretty()} {self.name}()"
        if self.tag == ValueTag.Variable:
            return f"{self.type.pretty()} {self.name}"
        if self.tag == ValueTag.BaseType:
            return self.name
        if self.tag == ValueTag.Pointer:
            return f"{self.type.pretty()}*"
        if self.tag == ValueTag.Array:
            return f"{self.type.pretty()}[{self.value}]"
        if self.tag == ValueTag.Struct:
            return f"struct {self.name}"
        if self.tag == ValueTag.Enum:
            return f"enum {self.name}"
        if self.tag == ValueTag.EnumValue:
            return f"{self.name} = {self.value}"
        if self.tag == ValueTag.Typedef:
            return self.name
        return None


class Store:
    def __init__(self):
        self.values: [Value] = []

    def put(self, val: Value):
        ix = len(self.values)
        assert val.id == ix
        self.values.append(val)

    def encode(self) -> bytes:
        data = BytesIO()
        write_u32(data, len(self.values))
        for val in self.values:
            write_u8(data, val.tag.value)
            write_str(data, val.name)
            write_u64(data, val.value if val.value else VALUE_VALUE_NONE)
            write_u32(data, val.type.id if val.type else VALUE_ID_NONE)
            write_u32(data, len(val.children))
            for child in val.children:
                write_u32(data, child.id)
        return data.getvalue()

    def decode(self, data: bytes):
        data = BytesIO(data)

        # Values
        value_count = read_u32(data)
        for id in range(0, value_count):
            val = Value()
            val.id = id
            val.tag = ValueTag(read_u8(data))
            val.name = read_str(data)
            val.value = read_u64(data)
            if val.value == VALUE_VALUE_NONE:
                val.value = None

            # Note: 'type' and 'children' are just id's, they are decoded later
            val.type = read_u32(data)
            child_count = read_u32(data)
            for child_ix in range(0, child_count):
                val.children.append(read_u32(data))
            self.values.append(val)

        # Convert id's to references
        for val in self.values:
            if val.type == VALUE_ID_NONE:
                val.type = None
            else:
                val.type = self.values[val.type]

            children = []
            for child_id in val.children:
                children.append(self.values[child_id])
            val.children = children

    def compile_units(self) -> [Value]:
        result = []
        for v in self.values:
            if v.tag == ValueTag.CompileUnit:
                result.append(v)
        return result

    def variables(self) -> [Value]:
        "Returns a list of top-level variables"
        result = []
        for cu in self.compile_units():
            for v in cu.children:
                if v.tag == ValueTag.Variable:
                    result.append(v)
        return result

    def find_variable(self, name: str) -> Value:
        "Find a top-level variable by name"
        for v in self.variables():
            if v.name == name:
                return v
        return None


# Helper functions for encode/decode

def write_u8(buf: BytesIO, value: int):
    buf.write(value.to_bytes(1, "little"))


def read_u8(buf: BytesIO) -> int:
    return int.from_bytes(buf.read(1), "little")


def write_u32(buf: BytesIO, value: int):
    buf.write(value.to_bytes(4, "little"))


def read_u32(buf: BytesIO) -> int:
    return int.from_bytes(buf.read(4), "little")


def write_u64(buf: BytesIO, value: int):
    buf.write(value.to_bytes(8, "little"))


def read_u64(buf: BytesIO) -> int:
    return int.from_bytes(buf.read(8), "little")


def write_str(buf: BytesIO, value: str):
    write_u32(buf, len(value))
    buf.write(value.encode())


def read_str(buf: BytesIO) -> str:
    len = read_u32(buf)
    return buf.read(len).decode()
