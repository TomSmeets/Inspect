import argparse
import time
import curses
from typing import Self
from value import Value, ValueTag
from client import Client


class RtNode:
    def __init__(self, value: Value,  name: str = None, offset: int = 0):
        self.name  = name
        self.value = value
        self.text  = None
        self.children = []
        self.offset = offset
        self.addr  = 0

        if self.value.tag == ValueTag.Variable:
            self.offset = self.value.value

        if not self.name:
            self.name = self.value.pretty()

    def update(self, client: Client, addr: int):
        # Add array/struct offset
        self.addr = addr + self.offset
        self.text = None
        type: Value = self.value
        while True:
            if type == None:
                break
            elif type.tag == ValueTag.Variable:
                type = type.type()
            elif type.tag == ValueTag.Typedef:
                type = type.type()
            elif type.tag == ValueTag.Pointer:
                self.addr = client.read_int(self.addr, type.value)
                type = type.type()
                if self.addr == 0:
                    self.text = "NULL"
                    break
            elif type.tag == ValueTag.Enum:
                self.text = "ENUM"
                break
            elif type.tag == ValueTag.Struct:
                self.text = "{}"
                break
            elif type.tag == ValueTag.Array:
                self.text = "[]"
                break
            elif type.tag == ValueTag.BaseType:
                data = client.read_int(self.addr, type.value)
                if type.name == "char":
                    self.text = f"{str(data)} ({repr(chr(data))})"
                else:
                    self.text = str(data)
                break
            else:
                break

        for c in self.children:
            c.update(client, self.addr)

    def expand(self):
        if self.value.tag == ValueTag.Namespace:
            self.children = [RtNode(n) for n in self.value.children]
            return

        type: Value = self.value.type()
        while True:
            if type == None:
                break
            elif type.tag == ValueTag.Variable:
                type = type.type()
            elif type.tag == ValueTag.Typedef:
                type = type.type()
            elif type.tag == ValueTag.Pointer:
                type = type.type()
            elif type.tag == ValueTag.Array:
                array_type: Value = type.type()
                size: int = 0
                while True:
                    if array_type.tag == ValueTag.Typedef:
                        array_type = array_type.type()
                    elif array_type.tag == ValueTag.BaseType:
                        size = array_type.value
                        break
                    elif array_type.tag == ValueTag.Pointer:
                        size = 8
                        break
                self.children = [RtNode(type.type(), name = f"[{i:2}]", offset = i * size, ) for i in range(0, type.value)]
                break
            elif type.tag == ValueTag.Struct:
                self.children = [RtNode(n) for n in type.children]
                break
            elif type.tag == ValueTag.BaseType:
                break
            elif type.tag == ValueTag.Enum:
                break
            elif type.tag == ValueTag.EnumValue:
                break
            else:
                break

    def collapse(self):
        self.children = []

    def pretty(self) -> str:
        return self.value.pretty()

    def draw(self, x: int = 0) -> list[(Self, int)]:
        text = f"{self.name}"
        # text = f"0x{self.addr:016x} {text}"
        # text = self.value.pretty()
        if self.text != None:
             text = f"{text} = {self.text}"
        lines = [(self, x, text)]
        for c in self.children:
            lines += c.draw(x + 1)
        return lines


class Gui:

    def __init__(self, client: Client):
        self.client = client

        # Tree of expanded nodes
        self.node = RtNode(client.root)
        self.node.expand()

        # Current highlighed line
        self.cursor = 0

        # Scroll offset
        self.scroll = 0

        # List of flattend nodes and indentation level
        self.lines: list[(RtNode, int, str)] = []

    def update(self):
        self.node.update(self.client, self.client.base_address)
        self.lines = [l for c in self.node.children for l in c.draw()]
        self.cursor_update()

    def cursor_update(self):
        if self.cursor < 0:
            self.cursor = 0
        if self.cursor >= len(self.lines):
            self.cursor = len(self.lines) - 1

    def cursor_node(self) -> RtNode:
        if self.lines == []:
            return None
        return self.lines[self.cursor][0]

    def cursor_x(self) -> int:
        if self.lines == []:
            return 0
        return self.lines[self.cursor][1]

    def cursor_prev(self) -> bool:
        if self.cursor == 0:
            return False
        self.cursor -= 1
        return True

    def cursor_next(self) -> bool:
        if self.cursor + 1 >= len(self.lines):
            return False
        self.cursor += 1
        return True

    def cursor_down(self):
        if self.cursor_node().children == []:
            self.cursor_node().expand()
        if self.cursor_node().children != []:
            self.cursor_next()

    def cursor_up(self):
        cur_x = self.cursor_x()
        while self.cursor_prev():
            if self.cursor_x() < cur_x:
                break
        # if self.cursor_node().children != []:
        #     self.cursor_node().collapse()

    def cursor_toggle(self):
        if self.cursor_node().children == []:
            self.cursor_node().expand()
        else:
            self.cursor_node().collapse()

    def draw(self, scr):
        size_x = curses.COLS
        size_y = curses.LINES

        # Update scroll
        screen_pad = 6
        if self.scroll < self.cursor + screen_pad - size_y:
            self.scroll = self.cursor + screen_pad - size_y
        if self.scroll > self.cursor - screen_pad:
            self.scroll = self.cursor - screen_pad
        if self.scroll < 0:
            self.scroll = 0

        # Draw info
        y = 0
        cur_node = self.cursor_node()
        for node, x, text in self.lines[self.scroll :]:
            if y >= size_y:
                break

            indent = x * 4
            if indent >= size_x:
                indent = size_x - 1
            text = f"| {text}"

            # value = node.read_value(self.client)
            # if value:
            #     text = text + " = " + value

            # Limit length
            text = text[: size_x - indent]

            if node == cur_node:
                scr.addstr(y, indent, text, curses.A_REVERSE)
            else:
                scr.addstr(y, indent, text)
            y += 1


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--host", default="localhost", help="Router host")
    parser.add_argument("-p", "--port", type=int, default=1234, help="Router port")
    parser.add_argument("-s", "--symbol", default="DEBUG_DATA", help="Debug table name")
    args = parser.parse_args()

    client = Client()
    client.connect(args.host, args.port, args.symbol)

    gui = Gui(client)

    def gui_main(scr):
        curses.curs_set(0)
        curses.halfdelay(10)
        while True:
            gui.update()

            curses.update_lines_cols()
            scr.clear()
            gui.draw(scr)
            scr.refresh()

            try:
                k = scr.getkey()
            except:
                k = None

            if k == "q":
                break
            elif k == "j":
                gui.cursor_next()
            elif k == "k":
                gui.cursor_prev()
            elif k == "l":
                gui.cursor_down()
            elif k == " ":
                gui.cursor_toggle()
            elif k == "h":
                gui.cursor_up()

    curses.wrapper(gui_main)


if __name__ == "__main__":
    main()
