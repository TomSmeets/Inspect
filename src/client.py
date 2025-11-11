import socket
import zlib
import struct
from store import Store


# Magic value (u64)
# Used for finding the database in the binary file
# This was randomly generated using `openssl rand -hex 8`
DB_MAGIC: bytes = bytes([0xA1, 0x07, 0x23, 0x45, 0xF0, 0x5C, 0xAE, 0x4C])


# Implement this interface
class Client:
    def info(self) -> int:
        """Return address of the DEBUG_DATA section"""
        pass

    def read(self, addr: int, size: int) -> bytes:
        """Read memory from address"""
        pass

    def write(self, addr: int, data: bytes):
        """Write memory to address"""
        pass


class Runtime:

    def __init__(self, client: Client):
        self.client = client
        self.store = Store()
        self.base_address: int = 0

    def read_database(self):
        addr = self.client.info()
        header = self.client.read(addr, 16)
        magic = header[0:8]
        max_size = int.from_bytes(header[8:12], "little")
        data_size = int.from_bytes(header[12:16], "little")
        assert magic == DB_MAGIC
        assert data_size <= max_size
        store_data = self.client.read(addr + 16, data_size)
        store_data = zlib.decompress(store_data)
        self.store.decode(store_data)
        print(f"Found {len(self.store.values)} items")

        self.base_address = addr - self.store.find_variable("DEBUG_DATA").value
        print(f"Base address: {self.base_address:#x}")

    def read(self, addr: int, size: int) -> bytes:
        return self.client.read(addr, size)

    def write(self, addr: int, data: bytes):
        self.client.write(addr, data)

    def read_int(self, addr: int, len: int) -> int:
        return int.from_bytes(self.client.read(addr, len), "little")

    def write_int(self, addr: int, len: int, data: int):
        self.client.write(addr, data.to_bytes(len, "little"))
