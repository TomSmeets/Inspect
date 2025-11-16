from io import BytesIO
from value import Value, ValueTag


def encode(root: Value) -> bytes:
    # value, children, pairs
    values: list[(Value, list[int])] = []

    # (value, id) pairs
    mapping: dict[Value, int] = {}

    def store(val: Value) -> int:
        if val in mapping:
            return mapping[val]

        # Append new value
        id = len(values)
        values.append((val, []))
        mapping[val] = id

        # Visit children
        for child in val.children:
            values[id][1].append(store(child))

        return id

    store(root)

    # Encode data
    data = BytesIO()
    write_u32(data, len(values))
    for val, _ in values:
        write_u8(data, val.tag.value)
    for val, _ in values:
        write_u32(data, len(val.name))
    for val, _ in values:
        data.write(val.name.encode())
    for val, _ in values:
        write_u64(data, val.value)
    for val, children in values:
        write_u32(data, len(children))
    for val, children in values:
        for child in children:
            write_u32(data, child)
    return data.getvalue()


def decode(data: bytes) -> Value:
    data = BytesIO(data)

    # Values
    value_count = read_u32(data)
    ix_list = range(0, value_count)
    tag_list = [ValueTag(read_u8(data)) for _ in ix_list]
    name_len_list = [read_u32(data) for _ in ix_list]
    name_list = [data.read(l).decode() for l in name_len_list]
    value_list = [read_u64(data) for _ in ix_list]
    child_len_list = [read_u32(data) for _ in ix_list]
    child_list = [[read_u32(data) for _ in range(0, l)] for l in child_len_list]

    values = [Value(tag, name, value) for tag, name, value in zip(tag_list, name_list, value_list)]
    for val, children in zip(values, child_list):
        val.children = [values[child] for child in children]

    # Return root node (always the first)
    return values[0]


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
