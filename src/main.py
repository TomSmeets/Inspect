import sys
import time
import zlib
import struct
from client import Client, Runtime
from store import Store, Value, ValueTag
from dwarfdb import DwarfDB
from curses import wrapper
import socket

# Magic value (u64)
# Used for finding the database in the binary file
DB_MAGIC: bytes = bytes([0xA1, 0x07, 0x23, 0x45, 0xF0, 0x5C, 0xAE, 0x4C])


def help_header(size):
    magic_1 = int.from_bytes(DB_MAGIC[0:4], "little")
    magic_2 = int.from_bytes(DB_MAGIC[4:8], "little")
    word_count = (size + 3) // 4
    name = "DEBUG_DATA"
    print("Add the following code to reseve space for debug data.")
    print("---------------- Example Code for C/C++ ----------------")
    print(f"// Debug data table used by the `inspect` debug tooling")
    print(f"unsigned int {name}[{word_count}] = {{")
    print(f"    0x{magic_1:8x},")
    print(f"    0x{magic_2:8x},")
    print(f"    sizeof({name})")
    print(f"}};")
    print("--------------------------------------------------------")

    # print("---------------- Example Code for Rust -----------------")
    # print(f"const {name}_SIZE: u32 = {word_count};")
    # print(f"#[used]")
    # print(f"pub static mut DEBUG_DATA: [u32; DEBUG_DATA_SIZE as usize] = {{")
    # print(f"    let mut data = [0u32; DEBUG_DATA_SIZE as usize];")
    # print(f"    data[0] = 0x{magic_1:8x};")
    # print(f"    data[1] = 0x{magic_2:8x};")
    # print(f"    data[2] = 4*DEBUG_DATA_SIZE;")
    # print(f"    data")
    # print(f"}};")
    # print("--------------------------------------------------------")


class SocketClient(Client):
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def info(self) -> int:
        self.sock.sendall(struct.pack("<B", 0))
        addr = struct.unpack("<Q", self.sock.recv(8))[0]
        return addr

    def read(self, addr: int, size: int) -> bytes:
        if size == 0:
            return bytes()

        self.sock.sendall(struct.pack("<BQQ", 1, addr, size))
        return self.sock.recv(size)

    def write(self, addr: int, data: bytes):
        self.sock.sendall(struct.pack("<BQQ", 2, addr, len(data)))
        self.sock.sendall(data)


def write_db(path: str, data: bytes):
    """Locate the debug table and write the data to it"""
    addr: int = None
    size: int = None

    full_size = len(data) + 16
    print("Looking for debug table header...")
    with open(path, "rb") as file:
        file_data: bytes = file.read()
        addr = file_data.find(DB_MAGIC)
        if addr < 0:
            print("ERROR: The DEBUG_DATA table was not found.")
            help_header(full_size)
            sys.exit(1)
            return

        size = int.from_bytes(file_data[addr + len(DB_MAGIC) : addr + len(DB_MAGIC) + 4], "little")
    print(f"Found table at {addr:#x} with size={size}")

    print(f"Writing table...")
    if full_size > size:
        print()
        print(f"ERROR: Debug talbe is too small, it should support at least {full_size} bytes.")
        help_header(full_size)
        sys.exit(1)
        return

    with open(path, "r+b") as file:
        file.seek(addr)
        file.write(DB_MAGIC)
        file.write(size.to_bytes(4, "little"))
        file.write(len(data).to_bytes(4, "little"))
        file.write(data)
        file.write(bytes(size - 16 - len(data)))
    return data


def patch(dwarf: str, bin: str):
    print(f"Reading debug data from '{dwarf}'...")
    db = DwarfDB()
    db.load_dwarf(dwarf)
    data = db.encode()
    print(f"Data size is {len(data) + 16} bytes")
    # data = zlib.compress(data)
    # print(f"Compressed size is {len(data)}")
    print(f"Writing debug data to '{bin}'...")
    write_db(bin, data)
    print("OK")


def connect(host: str, port: int):
    rt = Runtime(SocketClient(host, port))
    rt.read_database()

    addr = rt.store.find_variable("counter").value + rt.base_address
    rt.write_int(addr, 4, 1234)

    vars = rt.store.variables()
    while True:
        for v in vars:
            type = v.type.untypedef()
            value = None

            if v.value is None:
                value = "(optimized out)"
            else:
                addr = v.value + rt.base_address

                if type.tag == ValueTag.BaseType:
                    value = rt.read_int(addr, type.value)

                if type.tag == ValueTag.Array:
                    base = type.type.untypedef()

                    count = type.value
                    size = base.value

                    # Read entire data
                    if base.name == "char":
                        data = rt.read(addr, count * size)
                        value = repr(data.decode())

            if value is not None:
                print(f"{v.pretty()} = {value};")
            else:
                print(f"{v.pretty()};")
        time.sleep(1)


def show_usage():
    print(f"ERROR: Invalid command: '{" ".join(sys.argv)}'")
    print("")
    print("Usage:")
    print(f"  {sys.argv[0]} patch   <ELF_FILE>        | Write debug data to ELF file directly")
    print(f"  {sys.argv[0]} patch   <ELF_FILE> <BIN>  | Write debug data to any binary file")
    print(f"  {sys.argv[0]} connect [host] [port]     | Connect to a server")


def main():
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)

    if sys.argv[1] == "patch":
        if len(sys.argv) < 3:
            show_usage()
            sys.exit(1)

        input = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) >= 4 else input
        patch(input, output)
    elif sys.argv[1] == "connect":
        host = sys.argv[2] if len(sys.argv) >= 3 else "localhost"
        port = int(sys.argv[3]) if len(sys.argv) >= 4 else 1234
        connect(host, port)
    else:
        show_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
