use std::net::TcpListener;
use std::io::Read;
use std::io::Write;

const DEBUG_DATA_SIZE: u32 = 64;

#[used]
pub static mut DEBUG_DATA: [u32; DEBUG_DATA_SIZE as usize] = {
    let mut data = [0u32; DEBUG_DATA_SIZE as usize];
    data[0] = 0x452307a1;
    data[1] = 0x4cae5cf0;
    data[2] = 4*DEBUG_DATA_SIZE;
    data
};

fn main() {
    println!("Hello World!");
    let listener = TcpListener::bind("127.0.0.1:1234").unwrap();
    for stream in listener.incoming() {
        let mut stream = stream.unwrap();
        println!("Connection established!");

        loop {
            let mut command = [ 0 ];
            let n = stream.read(&mut command);
            if !n.is_ok() {
                break;
            }
            println!("command: {}", command[0]);
            if command[0] == 0 {
                unsafe {
                    let kira = &DEBUG_DATA[0] as *const u32 as usize;
                    let bytes: [u8; 8] = kira.to_le_bytes();
                    stream.write(&bytes).unwrap();
                }
            }
        }
    }
}
