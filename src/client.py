import socket
import zlib
import struct
import store
from value import Value, ValueTag


class Client:
    def __init__(self):
        self.sock = None
        self.root = None
        self.base_address = 0

    def connect(self, host: str, port: int, symbol_name: str = "DEBUG_DATA"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        # Request deubg_data table address
        addr = self.info()

        # Read table header
        header = self.read(addr, 16)
        magic = header[0:8]
        max_size = int.from_bytes(header[8:12], "little")
        data_size = int.from_bytes(header[12:16], "little")
        print(f"Found Header magic={magic.hex()}, max_size={max_size}, data_size={data_size}")

        # Read and parse entire table
        store_data = self.read(addr + 16, data_size)
        store_data = zlib.decompress(store_data)
        self.root = store.decode(store_data)
        print(f"Found {len(self.root.children)} CU's with {len(self.root.variables())} variables")

        # Calculate base_address
        base_var = self.find_variable(symbol_name)
        self.base_address = addr - base_var.value
        print(f"Base address: {self.base_address:#x}")

    # The protocol commands
    def info(self) -> int:
        """Return address of the DEBUG_DATA section"""
        self.sock.sendall(struct.pack("<B", 0))
        addr = struct.unpack("<Q", self.sock.recv(8))[0]
        return addr

    def read(self, addr: int, size: int) -> bytes:
        """Read memory from address"""
        if size == 0:
            return bytes()

        self.sock.sendall(struct.pack("<BQQ", 1, addr, size))
        return self.sock.recv(size)

    def write(self, addr: int, data: bytes):
        """Write memory to address"""
        self.sock.sendall(struct.pack("<BQQ", 2, addr, len(data)))
        self.sock.sendall(data)

    # Helper functions
    def read_int(self, addr: int, len: int) -> int:
        return int.from_bytes(self.read(addr, len), "little")

    def write_int(self, addr: int, len: int, data: int):
        self.write(addr, data.to_bytes(len, "little"))

    def find_variable(self, name: str) -> Value:
        for var in self.root.variables():
            if var.name == name:
                return var
        return None
