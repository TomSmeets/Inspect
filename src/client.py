import socket
import zlib
import struct
import store
import argparse
import time
import curses
from typing import Self
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

    def read_int(self, addr: int, len: int) -> int:
        return int.from_bytes(self.client.read(addr, len), "little")

    def write_int(self, addr: int, len: int, data: int):
        self.client.write(addr, data.to_bytes(len, "little"))


class Runtime:

    def __init__(self, client: Client):
        self.client = client
        self.root = None
        self.base_address = 0

    def find_variable(self, name: str) -> (Value, Value):
        for cu in self.root.children:
            for var in cu.children:
                if var.name == name:
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


class RtNode:
    def __init__(self, value: Value):
        self.value = value
        self.children = []

    def expand(self):
        self.children = [RtNode(n) for n in self.value.children]

    def collapse(self):
        self.children = []

    def pretty(self) -> str:
        return self.value.pretty()

    def draw(self, x: int = 0) -> list[(Self, int)]:
        lines = [(self, x)]
        for c in self.children:
            lines += c.draw(x + 1)
        return lines


def main(scr):
    curses.curs_set(0)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--host", default="localhost", help="Router host")
    parser.add_argument("-p", "--port", type=int, default=1234, help="Router port")
    args = parser.parse_args()

    client = Client(args.host, args.port)
    rt = Runtime(client)
    rt.read_database("DEBUG_DATA")

    cursor = 0
    scroll = 0

    root = RtNode(rt.root)
    root.expand()

    while True:
        scr.clear()
        curses.update_lines_cols()

        lines = [l for c in root.children for l in c.draw()]
        if cursor < 0:
            cursor = 0
        if cursor >= len(lines):
            cursor = len(lines) - 1

        screen_pad = 6
        if scroll < cursor + screen_pad - curses.LINES:
            scroll = cursor + screen_pad - curses.LINES

        if scroll > cursor - screen_pad:
            scroll = cursor - screen_pad

        if scroll < 0:
            scroll = 0

        cur_node, cur_node_x = lines[cursor]

        y = 0
        scr.addstr(y, 0, f"{cursor} / {len(lines)} {curses.LINES} {curses.COLS}")
        y += 1

        for node, x in lines[scroll:]:
            if y >= curses.LINES:
                break

            if node == cur_node:
                scr.addstr(y, 10 + x * 4, node.value.name, curses.A_REVERSE)
            else:
                scr.addstr(y, 10 + x * 4, node.value.name)
            y += 1

        scr.refresh()
        k = scr.getkey()
        if k == "q":
            break
        elif k == "j":
            cursor += 1
        elif k == "k":
            cursor -= 1
        elif k == "l":
            if cur_node.children == []:
                cur_node.expand()
            cursor += 1
        elif k == " ":
            if cur_node.children == []:
                cur_node.expand()
            else:
                cur_node.collapse()
        elif k == "h":
            if cur_node.children == []:
                while cursor > 0:
                    cursor -= 1
                    n, x = lines[cursor]
                    if x < cur_node_x:
                        n.collapse()
                        break
            else:
                cur_node.collapse()

    # while True:
    #     print("")
    #     for v in rt.root.variables():
    #         print(v.pretty(), end="")
    #         type = v.type().untypedef()

    #         if type.tag == ValueTag.BaseType:
    #             print(" = ", end="")
    #             print(rt.read_int(rt.base_address + v.value, type.value), end="")

    #         print(";")


if __name__ == "__main__":
    curses.wrapper(main)
