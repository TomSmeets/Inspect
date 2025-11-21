import argparse
import time
from value import Value, ValueTag
from client import Client

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--host", default="localhost", help="Router host")
    parser.add_argument("-p", "--port", type=int, default=1234, help="Router port")
    parser.add_argument("-s", "--symbol", default="DEBUG_DATA", help="Debug table name")
    args = parser.parse_args()

    client = Client()
    client.connect(args.host, args.port, args.symbol)
    val = client.find_variable("_SEGGER_RTT")

    rtt_addr = client.base_address + val.value
    rtt_size_addr = rtt_addr + 40
    rtt_woff_addr = rtt_addr + 44
    rtt_buff_ptr_addr = rtt_addr + 44 - 0xc + 0xc0

    max_size = client.read_int(rtt_size_addr, 4)
    buff_addr = client.read_int(rtt_buff_ptr_addr, 8)
    print(max_size)
    print(f"{buff_addr:x}")

    last_off = 0
    while True:
        new_off = client.read_int(rtt_woff_addr, 4)
        print(new_off)
        if new_off == last_off:
            time.sleep(0.1)
            continue
        if new_off < last_off:
            new_off = max_size
        print("K: ", client.read(buff_addr + last_off, new_off - last_off).decode())
        last_off = new_off % max_size


if __name__ == '__main__':
    main()
