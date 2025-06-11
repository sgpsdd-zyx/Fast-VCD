import argparse
from vcd_reader import VCDReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo for VCDReader")
    parser.add_argument("vcd_file", help="Path to VCD file")
    parser.add_argument("pin", help="Pin to monitor")
    parser.add_argument("--start", type=int, default=0, help="Start time")
    parser.add_argument("--end", type=int, help="End time")
    parser.add_argument("--netlist", help="Optional netlist file")
    args = parser.parse_args()

    reader = VCDReader(args.vcd_file, args.netlist)
    end_time = args.end
    if end_time is None:
        rows = reader.parser.get_rows()
        end_time = rows[-1] if rows else 0
    events = reader.get_flip_events(args.pin, args.start, end_time)
    for is_rising, ts in events:
        direction = "RISING" if is_rising else "FALLING"
        print(f"{direction} @ {ts}")


if __name__ == "__main__":
    main()
