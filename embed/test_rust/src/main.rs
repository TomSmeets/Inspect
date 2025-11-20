use std::ptr::null_mut;

mod inspect;

struct App {
    counter: u32,
    data1: &'static str,
    data2: String,
}

static mut APP: *mut App = null_mut();

fn main() {
    let mut app = App {
        counter: 1337,
        data1: "Hello World!",
        data2: "Hello World!".into(),
    };
    unsafe {
        APP = &mut app;
        println!("&APP         = {:p}", &raw const APP);
    }
    let h = inspect::inspect_start(1234);
    println!("&app         = {:p}", &app);
    println!("&app.counter = {:p}", &app.counter);
    println!("&app.data1   = {:p}", &app.data1);
    println!("&app.data2   = {:p}", &app.data2);
    h.join().unwrap();
}
