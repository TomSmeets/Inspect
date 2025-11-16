from value import Value
import argparse
import sys
import zlib
import time

import dwarfdb
import store
from value import Value, deduplicate, debug_print

opt_verbose = False
opt_magic = bytes.fromhex("a1072345f05cae4c")
opt_lang = "c"


def help_header(size: int):
    magic_1 = int.from_bytes(opt_magic[0:4], "little")
    magic_2 = int.from_bytes(opt_magic[4:8], "little")
    # Round up to nearest u32
    word_count = (size + 3) // 4
    name = "DEBUG_DATA"
    print("Add the following code to reseve space for debug data.")

    if opt_lang == "c":
        print("---------------- Example Code for C/C++ ----------------")
        print(f"// Debug data table used by the `inspect` debug tooling")
        print(f"unsigned int {name}[{word_count}] = {{")
        print(f"    0x{magic_1:8x},")
        print(f"    0x{magic_2:8x},")
        print(f"    sizeof({name})")
        print(f"}};")
        print("--------------------------------------------------------")
    elif opt_lang == "rust":
        print("---------------- Example Code for Rust -----------------")
        print(f"const {name}_SIZE: u32 = {word_count};")
        print(f"#[used]")
        print(f"pub static mut {name}: [u32; {name}_SIZE as usize] = {{")
        print(f"    let mut data = [0u32; {name}_SIZE as usize];")
        print(f"    data[0] = 0x{magic_1:8x};")
        print(f"    data[1] = 0x{magic_2:8x};")
        print(f"    data[2] = 4*{name}_SIZE;")
        print(f"    data")
        print(f"}};")
        print("--------------------------------------------------------")


def write_db(path: str, data: bytes):
    """Locate the debug table and write the data to it"""
    addr: int = None
    size: int = None

    full_size = len(data) + 16
    print(f"Looking for debug table header '{opt_magic.hex()}'...")
    with open(path, "rb") as file:
        file_data: bytes = file.read()
        addr = file_data.find(opt_magic)
        if addr < 0:
            print("ERROR: The DEBUG_DATA table was not found.")
            help_header(full_size)
            sys.exit(1)
            return

        size = int.from_bytes(file_data[addr + 8 : addr + 12], "little")
    print(f"Found table at addr={addr:#010x} with size={size} ({(size +1023) // 1024}K)")

    print("Writing table...")
    if full_size > size:
        print(f"ERROR: Not enogh reserved space, minimum table size is {full_size} bytes ({(full_size + 1023) // 1024}K)")
        help_header(full_size)
        sys.exit(1)
        return

    with open(path, "r+b") as file:
        # Keep header intact (magic + max_size)
        file.seek(addr + 12)
        # Write actual size
        file.write(len(data).to_bytes(4, "little"))
        # Write data
        file.write(data)
        # Clear rest of the table
        file.write(bytes(size - 16 - len(data)))
    return data


def patch(input: str, target: [str]):
    print(f"Reading debug data from '{input}'...")
    value = dwarfdb.load(input)

    if opt_verbose:
        for var in value.variables():
            print(f"{var.name}")

    print(f"Deduplicating...")
    t0 = time.time()
    deduplicate(value)
    t1 = time.time()
    debug_print(value)
    print(f"t: {t1-t0:.2f}")
    print(f"Encoding...")
    data = store.encode(value)
    print(f"Compressing...")
    data = zlib.compress(data)
    print(f"Final table size: {len(data) + 16} bytes")
    for t in target:
        print(f"Writing debug data to '{t}'...")
        write_db(t, data)
    print("OK")


def main():
    global opt_magic
    global opt_verbose

    # Randomly generated using:
    # > openssl rand -hex 8
    parser = argparse.ArgumentParser()
    parser.add_argument("FILE")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-m", "--magic", help=f"Table header of 8 bytes (default: {opt_magic.hex()})")
    parser.add_argument("-t", "--target", help="Apply changes to this file instead of input file", action="append")
    args = parser.parse_args()
    print(args)

    # Verbose
    opt_verbose = args.verbose

    # Target
    target = args.target or [args.FILE]

    # Custom magic if needed
    if args.magic:
        try:
            opt_magic = bytes.fromhex(args.magic)
        except:
            print("ERROR: Magic is not a list of hex digits.")
            sys.exit(1)

    if len(opt_magic) != 8:
        print("ERROR: Invalid magic size, expecting 8 bytes (16 hex digits)")
        print("You can generate one with `openssl rand -hex 8` for example.")
        sys.exit(1)

    patch(args.FILE, target)


if __name__ == "__main__":
    main()
