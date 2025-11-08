# Inspect

Zero-overhead interface for real time Debugging and UI prototyping.

The `inspect` tool embeds debug information into your firmware or executable, exposing types and global variables at runtime.
The communication protocol betrween the GUI and the target is up to you and can be embedded into any existing communication protocol.
The communication protocol is kept as minimal as possible to make implemetaiton as simple as possible.

## How do I use this?

There are two things you need to do to start using this debug interface.
1. Reserve space for a `DEBUG_DATA` table in your firmware by defining a global array.
2. Call `inspect patch <ELF>` after building your firmware to write the debug information to this table
3. Implement the `info`, `read` and `write` command handling on te target and on the GUI side over any protocol you like.

## The Debug Info Table

Compiled `ELF` binaries contain information about all types and data embedded in `DWARF` format when compiled with `-g`.
This data is however usually not kept around when flashing embedded devices.
the `inspect patch` tool reads this information and embeds it into the normal address space for global variables.

This data can then be directly read from memory at runtime.


A real time debugger GUI can connect to the target over a pre existing custom protocol, for example: UART, Ethernet, etc..,
and read this embedded debug information using memory read commands.
Using this information the gui now knoows exactly wehre which variable is located, and can then display a live veiw of these variabels and their values.


To reserve space in your executable for the debug information, incldue the following C / C++ code.
It is up to you how big you make this table. The patch tool will report how much space is actually needed.

```c
// The following C/C++ code reserves space for the debug_data table
// which is filled in by `inspect patch` after compilation has finished.
// Note that the actual table size is `4*256` in this case.
unsigned int DEBUG_DATA[256] = {
    0x452307a1,  0x4cae5cf0, // A unique 'magic' value used to locate this table after compilation
    sizeof(DEBUG_DATA),      // The maximum table size is also embedded into the header for bounds checking
};
```

<details>
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
