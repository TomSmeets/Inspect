import argparse
import time
import curses
from typing import Self
from value import Value, ValueTag
from client import Client


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



def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--host", default="localhost", help="Router host")
    parser.add_argument("-p", "--port", type=int, default=1234, help="Router port")
    parser.add_argument("-s", "--symbol", default="DEBUG_DATA", help="Debug table name")
    args = parser.parse_args()

    client = Client()
    client.connect(args.host, args.port, args.symbol)

    def gui(scr):
        curses.curs_set(0)

        cursor = 0
        scroll = 0

        root = RtNode(client.root)
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
                    scr.addstr(y, x * 4, node.value.name, curses.A_REVERSE)
                else:
                    scr.addstr(y, x * 4, node.value.name)
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

    curses.wrapper(gui)

if __name__ == "__main__":
    main()
