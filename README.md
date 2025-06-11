# Fast-VCD
High-Performance Python VCD Parser built with PyBind.

# History

This was initially developed during the Winter 2025 Semester of EECS470 (University of Michigan, Computer Architecture) to accelerate our internal debugging tools. 

All are free to use.

# Installing

You will need:

- A compiler that supports C++20
- Python3 

Install the python dependencies:
```bash
pip3 install -r requirements.txt
```

Build the C++ backend:
```bash
python3 setup.py build_ext --inplace
```

# Using

```python
import vcd_parser

if __name__ == "__main__":
    # Create an instance of VCDParser with a filename
    parser = vcd_parser.VCDParser("p3_cpu.vcd")

    # Query a row
    row = parser.query_row(0)

    print(row)
```

## Extracting flip events

`VCDReader` builds on top of `vcd_parser.VCDParser` and provides a simple way to
retrieve signal transitions for a given pin. The parser exposes a `query_cell`
function so the reader only loads the requested signal, and it performs a binary
search on the timestamps so it can jump directly to the requested time window.

### With netlist file (recommended)
When providing a netlist file, use signal names as they appear in the netlist:

```python
from vcd_reader import VCDReader

reader = VCDReader("simulation.vcd", "design.v")
flips = reader.get_flip_events("CLK", 0, 1000)  # Use netlist signal name
for rising, ts in flips:
    print("rise" if rising else "fall", ts)
```

### Without netlist file
When not providing a netlist, use the full hierarchical signal names from the VCD file:

```python
from vcd_reader import VCDReader

reader = VCDReader("simulation.vcd")
flips = reader.get_flip_events("tb.CLK", 0, 1000)  # Use full VCD signal name
for rising, ts in flips:
    print("rise" if rising else "fall", ts)
```

### Command-line demo

`demo.py` exposes this functionality via a small CLI:

```bash
# With netlist (use netlist signal names)
python3 demo.py wave.vcd CLK --start 0 --end 1000 --netlist design.v

# Without netlist (use full VCD signal names)
python3 demo.py wave.vcd tb.CLK --start 0 --end 1000
```
