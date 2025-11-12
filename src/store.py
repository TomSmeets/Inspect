from io import BytesIO
from value import Value, ValueTag

def encode(root: Value) -> bytes:
    # (value, child_ix) pairs
    values = []

    def find(val: Value):
        for i,(v, _) in enumerate(values):
            if v == val:
                return i
        return None

    def store(val: Value):
        found = find(val)

        # Already exists
        if found is not None:
            return found

        # Append new value
        id = len(values)
        values.append((val, []))

        # Visit children
        for child in val.children:
            values[id][1].append(store(child))

        return id

    store(root)

    # Encode data
    data = BytesIO()
    write_u32(data, len(values))
    for (val, children) in values:
        write_u8(data, val.tag.value)
        write_str(data, val.name)
        write_u64(data, val.value)
        write_u32(data, len(children))
        for child in children:
            write_u32(data, child)
    return data.getvalue()
   
def decode(data: bytes) -> Value:
    data = BytesIO(data)

    # Values
    value_count = read_u32(data)
    values = []
    for id in range(0, value_count):
        tag  = ValueTag(read_u8(data))
        name = read_str(data)
        value = read_u64(data)
        print(f"decode {tag} {name}")

        val = Value(tag, name, value)

        child_count = read_u32(data)
        child_list = []
        for child in range(0, child_count):
            child_list.append(read_u32(data))
        values.append((val, child_list))

    for (val, child_list) in values:
        val.children = [ values[child] for child in child_list ]

    # Return root node (always the first)
    return values[0][0]

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
