use std::io::Read;
use std::io::Write;
use std::net::TcpListener;
use std::slice::from_raw_parts;

const DEBUG_DATA_SIZE: u32 = 64 * 1024 / 4;

#[used]
static DEBUG_DATA: [u32; DEBUG_DATA_SIZE as usize] = {
    let mut data = [0u32; DEBUG_DATA_SIZE as usize];
    data[0] = 0x452307a1;
    data[1] = 0x4cae5cf0;
    data[2] = 4 * DEBUG_DATA_SIZE;
    data
};

fn inspect_thread(port: u16) {
    let listener = TcpListener::bind(("127.0.0.1", port)).unwrap();
    for stream in listener.incoming() {
        let mut stream = stream.unwrap();
        println!("Connection established!");

        loop {
            let mut command = [0];
            if stream.read_exact(&mut command).is_err() {
                break;
            }
            println!("command: {}", command[0]);
            match command[0] {
                0 => {
                    let addr = &DEBUG_DATA[0] as *const u32 as u64;
                    stream.write(&addr.to_le_bytes()).unwrap();
                }
                1 => {
                    // Read
                    // i64 addr
                    // i64 size
                    let mut args = [0; 8 * 2];
                    stream.read_exact(&mut args).unwrap();
                    let addr = u64::from_le_bytes(args[0..8].try_into().unwrap());
                    let size = u64::from_le_bytes(args[8..16].try_into().unwrap());
                    println!("addr={:#x} size={}", addr, size);
                    unsafe {
                        stream
                            .write_all(from_raw_parts(addr as *const u8, size as usize))
                            .unwrap();
                    }
                }
                2 => {}
                _ => (),
            }
        }
    }
}

pub fn inspect_start(port: u16) -> std::thread::JoinHandle<()> {
    return std::thread::spawn(move || inspect_thread(port));
}
