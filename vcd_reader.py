# VCDReader module for extracting flip events from VCD files.
from __future__ import annotations

import bisect
import os
from typing import List, Tuple

import vcd_parser


class VCDReader:
    """Helper class built on top of :class:`vcd_parser.VCDParser`.

    Parameters
    ----------
    vcd_path : str
        Path to the VCD file to parse.
    netlist_path : str, optional
        Optional path to a netlist file. When provided, ``get_flip_events``
        will verify that the requested ``target_pin`` exists within the file
        using a simple text search.
    """

    def __init__(self, vcd_path: str, netlist_path: str | None = None) -> None:
        self.parser = vcd_parser.VCDParser(vcd_path)
        self.netlist_contents: str | None = None
        if netlist_path is not None and os.path.exists(netlist_path):
            with open(netlist_path, "r", encoding="utf-8", errors="ignore") as f:
                self.netlist_contents = f.read()

    def _validate_pin(self, target_pin: str) -> None:
        if self.netlist_contents is not None and target_pin not in self.netlist_contents:
            raise ValueError(f"Pin '{target_pin}' not found in provided netlist")

    def get_flip_events(
        self, target_pin: str, start_time: int, end_time: int
    ) -> List[Tuple[bool, int]]:
        """Return a list of signal transitions for ``target_pin``.

        Parameters
        ----------
        target_pin : str
            Signal name to watch.
        start_time : int
            Inclusive start timestamp.
        end_time : int
            Inclusive end timestamp.

        Returns
        -------
        List[Tuple[bool, int]]
            ``(is_rising, timestamp)`` tuples where ``is_rising`` is ``True`` for
            a 0->1 transition and ``False`` for a 1->0 transition.
        """
        if start_time > end_time:
            raise ValueError("start_time must not exceed end_time")

        self._validate_pin(target_pin)

        times = self.parser.get_rows()
        events: List[Tuple[bool, int]] = []

        # Find the first and last relevant indices using binary search.
        start_idx = bisect.bisect_left(times, start_time)
        end_idx = bisect.bisect_right(times, end_time)

        prev_val = None

        for idx in range(start_idx, end_idx):
            t = times[idx]

            cur_val = self.parser.query_cell(idx, target_pin)
            if not cur_val:
                # Pin not present in this row
                continue

            if prev_val is not None and cur_val != prev_val:
                is_rising = prev_val == "0" and cur_val == "1"
                is_falling = prev_val == "1" and cur_val == "0"
                if is_rising or is_falling:
                    events.append((is_rising, t))
            prev_val = cur_val

        return events
