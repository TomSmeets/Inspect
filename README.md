# Inspect

Zero overhead Embedded Debugging over your own protocol

The protocol you are are going to use should support the following commands
- info()
- read()
- write()

Client sends `info()` request --> Target responds with two mcus `[0x1234, 0x4567]`

This tool consists of two parts:
- The `inspect patch` command embeds debug information into a executable
- The `inspect patch` command embeds debug information into a executable

```
+------+                        +--------+
| GUI  | <--- Any Protocol ---> | Target |
+-------                        +--------+
```


## How does it work?
- The `inspect patch` will convert the debug symbols to a compact format and write it to a predefined global variable in the executable.
- This data can be read and used at runtime
in DWARF debug data from a ELF executable/firmware image
- Write the debug data to the '.data' section
and writes a compact version to a predefined global variable.

This global variable can be read by the application during

This data is converted to a more compact internal representation and written back to the `.data` section in the executable.
This data is now part of the executabe and can be accessed at runtime.
This

## How to use?

Reserve space for a debug information table in your executable.
This table should start with magic value followed by the size of the buffer.

For C or C++
```c
unsigned int DEBUG_DATA[4*1024] = {
    0x452307a1, 0x4cae5cf0, // Magic Value
    sizeof(DEBUG_DATA),     // Buffer size
};
```

For Rust:
```rust
```

## Patch
``
``


## Protocol

- Info() -> [(id, name, addr)]
- Read(id: int, addr: int, size: int) -> bytes
- Write(id: int, addr: int, data: int)
- Call(id: int, addr: int)


The `Info` command discovers all MCU's that are available.

You are supposed to implement this protocol yourself, by embedding it into the existing communication protocol.

A suggested encoding could be as folllows:
- Info:  0: u8                                            -> count: u32, [id: u32, name_len: u32, name: [u8], addr: u64]
- Read:  1: u8, id: u32, addr: u32, size: u32             -> data: [u8]
- Write: 2: u8, id: u32, addr: u32, size: u32, data: [u8]
- Call:  3: u8, id: u32,

If your target only supports a limited size you can split the read/write commands into multiple parts.
For 64 bit address spaces use `u64` for the address field.
The `Write` and `Call` commands are optional.

## File format
Debug data is embedded into the final frimware or executable.



## ELF

### Type info
Type information is parsed from the DWARF debug symbols

### Command Reference
Each command starts wtith 3 64 bit integers `[ type, a1, a2 ]`

The Read Command `[0, addr, size]` returns `size` bytes of data

The Write Command `[1, addr, size]` is folowed by `size` bytes of data

The Info command `[2, *, *]` returns the base address for global variables

## GDB Server
An alternative is to support the gdb server protocol.

On the MCU Target supports only the most basic commands:
- read
- write

Gdb ui with live view

## Usefull tools

The tool `llvm-dwarfdump` is very usefull for decoding dwarf data.

# Ideas

- Data toch op chip, met query functie/
  - Dwarf direct mee linken (kan)
  - Generated C code voor typeinfo + list of globals
    - Kan uit dwarf generaten
    - Maak custom 'dwarfdump' in python, is nice en generic
    - Json(?) kan ook, of een binary type, of met embeded thypes
    - soort "Simple dwarf" format
      - tag, name, members
        (*) -> struct -> []
        simpele table:
          [id] = { enum kind, char *name, int64 size/count/, int id[] }

          [0] = { pointer, "",       -, [1] }
          [1] = { typedef, "App",    -, [2] }
          [2] = { struct,  "App",    -, [3, 4, 5] }
          [3] = { field,  "message", -, [] }
          [4] = { field,  "App",     -, [0] }
          [5] = { field,  "count",   -, [6] }
          [5] = { base,   "int",     -, [6] }

```

```

- Router app, die embedded proto praat, dan meerdere ui's
- Begin met curses interface
  1. Basic dwarf Type explorer (staat los van values namelijk)
  2. Add values read

## UI
- vscode
- http / electron



# How to find base address

```
static const Dwarf_Var DWARF_VARS[] = {
    {0, DWARF_base_type, "void", 0, 0},
    {1, DWARF_compile_unit, "main2.c", 0, 0, 1, (unsigned int[]){2, }},
    {2, DWARF_variable, "DWARF_VARS", 0, 3},
    {3, DWARF_array, "", 29, 4},
    {4, DWARF_const, "", 0, 5},
    {5, DWARF_typedef, "Dwarf_Var", 0, 6},
    {6, DWARF_struct, "", 0, 0, 7, (unsigned int[]){7, 9, 24, 28, 30, 31, 32, }},
    ...
```

1. somehow get one pointer to DWARF_VARS
2. scan DWARF_VARS, and find itself 'DWARF_VARS'
  - we now know the size of the array -> 29 in this case
  - we also know the base pointer, it is: (&DWA-RF_VARS) - var.offset



# Router

```
UI1 \
UI1 --- Router ~~(Mystery protocol)~~ handler
UI2 /
```

# Commands
Info()                   -> int    | Returns Address to DWARF_VARS structure (include size?)
Read(addr, size)         -> bytes  | Returns memory at requested location
Write(addr, size, bytes)           | Write memory at location

Write | addr | size | Writes memory to requested location


# Patching ELF / bin

- search for secret/uuid
- replace region with data
  - we need to serialize however

## Header
- u32 magic0
- u32 magic1
- u32 max_size
- u32 used_size
- u32 version

```
// Debug info table,
// filled in later with serialized dwarf data
#define MAX_SIZE (4*1024)
unsigned int DEBUG_DATA[MAX_SIZE/4] = { 0x1234, 0x1234, MAX_SIZE, 0, 0 }
```

## Data
- u32 tag
- u32 name_len
- u8 name[name_len]
- u8 pad_until_next_u32[]
- u64 value
- u32 type
- u32 child_count
- u32 children[child_count]

## Command ideas
- Call? could work, start with void fcn(void) functions.
