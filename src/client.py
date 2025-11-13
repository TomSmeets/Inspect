import socket
import zlib
import struct
import store
import argparse
import time
from value import Value, ValueTag

class Client:
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

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

class Runtime:

    def __init__(self, client: Client):
        self.client = client
        self.root = None
        self.base_address = 0

    def find_variable(self, name: str) -> (Value, Value):
        for cu in self.root.children:
            for var in cu.children:
                if var.name ==name:
                    return (cu, var)
        return None
        

    def read_database(self, symbol_name: str = "DEBUG_DATA"):
        addr = self.client.info()
        header = self.client.read(addr, 16)
        magic = header[0:8]
        max_size = int.from_bytes(header[8:12], "little")
        data_size = int.from_bytes(header[12:16], "little")
        print(f"Found Header magic={magic.hex()}, max_size={max_size}, data_size={data_size}")
        store_data = self.client.read(addr + 16, data_size)
        store_data = zlib.decompress(store_data)
        self.root = store.decode(store_data)
        print(f"Found {len(self.root.children)} CU's with {len(self.root.variables())} variables")

        base_cu, base_var = self.find_variable(symbol_name)
        print(f"Found '{base_var.name}' in '{base_cu.name}'")
        self.base_address = addr - base_var.value
        print(f"Base address: {self.base_address:#x}")

    def read(self, addr: int, size: int) -> bytes:
        return self.client.read(addr, size)

    def write(self, addr: int, data: bytes):
        self.client.write(addr, data)

    def read_int(self, addr: int, len: int) -> int:
        return int.from_bytes(self.client.read(addr, len), "little")

    def write_int(self, addr: int, len: int, data: int):
        self.client.write(addr, data.to_bytes(len, "little"))


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--host", default="localhost", help="Router host")
    parser.add_argument("-p", "--port", type=int, default=1234, help="Router port")
    args = parser.parse_args()

    client = Client(args.host, args.port)
    rt = Runtime(client)
    rt.read_database("DEBUG_DATA")

    while True:
        print("")
        for v in rt.root.variables():
            print(v.pretty(), end="")
            type = v.type().untypedef()

            if type.tag == ValueTag.BaseType:
                print(" = ", end="")
                print(rt.read_int(rt.base_address + v.value, type.value), end="")

            print(";")
        time.sleep(1)


if __name__ == "__main__":
    main()
