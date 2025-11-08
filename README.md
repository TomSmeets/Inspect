# Inspect

Zero-overhead interface for real time Debugging and UI prototyping.

The `inspect` tool embeds debug information into your firmware or executable, exposing types and global variables at runtime.
The communication protocol betrween the GUI and the target is up to you and can be embedded into any existing communication protocol.
It is kept intentially minimal to make implementation as simple as possible.

## How to Use

To start using the debug interface:
- Reserve space for a `DEBUG_DATA` table in your firmware by defining a global array.
- Run `inspect patch <ELF>` after building your firmware to populate this talbe with debug information.
- Implement the handling of the `info`, `read` and `write` commands on both the target and GUI side over any protocol you choose.

## The Debug Info Table

COmpiled ELF binaries contain DWARF debug information about all types and data when compiled with `-g`.
However this information is usually discared when flashing embedded devices.

The `inspect` tool extracts this DWARF data and embeds it into the normal address space as a global variable.
At runtime, this table can be read directly from memory.

A real-time deubgger GUI can connect to the target over a pre-existing custom protocol (e.g., Serial, Bluetooth, Ethernet, ...)
and read this debug information using memory read commands.
With this information the GUI knows exactly where each variable is located and can display a live view of variables and thier values.

### Reserving space for the debug data

Include the following C/C++ code to reserve space in your executable for the debug information table.
The table size is configurable. the patch tool will report the actual space needed.

```c
// The following C/C++ code reserves space for the debug_data table
// which is filled in by `inspect patch` after compilation has finished.
// Note that the actual table size is `4*256` in this case.
unsigned int DEBUG_DATA[256] = {
    0x452307a1,  0x4cae5cf0, // Unique 'magic' value to locate this table after compilation
    sizeof(DEBUG_DATA),      // The maximum table size, used for bounds checking
};
```

<details>
<summary>Rust</summary>
Something simmilar will also work for other compiled languages. Here is an example for Rust:

```rust
const DEBUG_DATA_SIZE: u32 = 64;
#[used]
pub static mut DEBUG_DATA: [u32; DEBUG_DATA_SIZE as usize] = {
    let mut data = [0u32; DEBUG_DATA_SIZE as usize];
    data[0] = 0x452307a1;
    data[1] = 0x4cae5cf0;
    data[2] = 4*DEBUG_DATA_SIZE;
    data
};
```

</details>

## Communication Protocol

The communication protocol should support the following commands:

The `info` command returns a list of connecte devices. Each device can identifie itself with an uniqe id and optionally a name.
Each device should also return the address of it's `DEBUG_DATA` table in memory.
- `Info() -> [(id: int, name: str, addr: int)]`

Read `size` bytes of memory from device `id` at `address`.
This command returns a byte array of data contained in main memory of the requested `size`
- `Read(id: int, addr: int, size: int) -> bytes`

Write `size` bytes of data to device `id` at `address`.
This commands accepts an array of bytes. This data is written to the specified address in main memory.
- `Write(id: int, addr: int, data: bytes)`


## License

This software is free to use and MIT licensed. See LICENSE.txt for more information.

