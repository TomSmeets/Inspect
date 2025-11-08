use std::net::TcpListener;

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
        let stream = stream.unwrap();
        let _ = stream;
        println!("Connection established!");
    }
}
