# VCDReader module for extracting flip events from VCD files.
from __future__ import annotations

import bisect
import os
from typing import List, Tuple, Optional

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

    def _find_vcd_signal_name(self, netlist_pin: str) -> str:
        """Find the corresponding VCD signal name for a netlist pin name.
        
        Parameters
        ----------
        netlist_pin : str
            The pin name as it appears in the netlist (e.g., 'CLK', 'DI')
            
        Returns
        -------
        str
            The corresponding hierarchical signal name in the VCD file (e.g., 'tb.CLK')
            
        Raises
        ------
        ValueError
            If no matching signal is found in the VCD file
        """
        columns = self.parser.get_columns()
        
        # Search for signals that end with the netlist pin name
        # Priority order: tb.PIN, tb.DUT.PIN, then any other hierarchical match
        candidates = []
        
        for col in columns:
            if col.endswith('.' + netlist_pin) or col == netlist_pin:
                candidates.append(col)
        
        if not candidates:
            raise ValueError(f"Signal '{netlist_pin}' not found in VCD file. Available signals ending with '{netlist_pin}': None")
        
        # Prioritize signals: tb.PIN > tb.DUT.PIN > others
        for candidate in candidates:
            if candidate == f"tb.{netlist_pin}":
                return candidate
        
        for candidate in candidates:
            if candidate == f"tb.DUT.{netlist_pin}":
                return candidate
                
        # Return the first candidate if no priority match found
        return candidates[0]

    def _validate_pin(self, target_pin: str) -> None:
        if self.netlist_contents is not None:
            # For netlist validation, use the original pin name
            if target_pin not in self.netlist_contents:
                raise ValueError(f"Pin '{target_pin}' not found in provided netlist")

    def get_flip_events(
        self, target_pin: str, start_time: int, end_time: int
    ) -> List[Tuple[bool, int]]:
        """Return a list of signal transitions for ``target_pin``.

        Parameters
        ----------
        target_pin : str
            If netlist is provided: Signal name as it appears in the netlist (e.g., 'CLK', 'DI', 'WE').
            If no netlist: Full hierarchical signal name in VCD file (e.g., 'tb.CLK', 'tb.DUT.CLK').
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

        # Determine the VCD signal name based on whether netlist is provided
        if self.netlist_contents is not None:
            # With netlist: validate pin exists in netlist, then find VCD signal
            self._validate_pin(target_pin)
            try:
                vcd_signal_name = self._find_vcd_signal_name(target_pin)
                print(f"Using VCD signal '{vcd_signal_name}' for netlist pin '{target_pin}'")
            except ValueError as e:
                raise ValueError(f"Failed to find VCD signal for netlist pin '{target_pin}': {e}")
        else:
            # Without netlist: use the target_pin directly as VCD signal name
            vcd_signal_name = target_pin
            # Verify the signal exists in VCD file
            columns = self.parser.get_columns()
            if vcd_signal_name not in columns:
                raise ValueError(f"Signal '{vcd_signal_name}' not found in VCD file. "
                               f"Available signals: {len(columns)} total. "
                               f"Use --netlist option to enable automatic signal mapping from netlist names.")

        times = self.parser.get_rows()
        events: List[Tuple[bool, int]] = []

        # Find the first and last relevant indices using binary search.
        start_idx = bisect.bisect_left(times, start_time)
        end_idx = bisect.bisect_right(times, end_time)

        # Get the initial signal state before the time window to detect edge transitions
        prev_val = None
        if start_idx > 0:
            # Use binary search to efficiently find the most recent valid signal value
            # First, try a limited backward search for common cases
            search_limit = min(100, start_idx)  # Limit search to avoid performance issues
            for i in range(start_idx - 1, start_idx - 1 - search_limit, -1):
                initial_val = self.parser.query_cell(i, vcd_signal_name)
                if initial_val and initial_val in ["0", "1"]:
                    prev_val = initial_val
                    break
            
            # If limited search fails, do a more comprehensive search using binary approach
            if prev_val is None:
                # Binary search for the last valid signal change before start_time
                left, right = 0, start_idx - 1
                last_valid_idx = -1
                
                while left <= right:
                    mid = (left + right) // 2
                    mid_val = self.parser.query_cell(mid, vcd_signal_name)
                    
                    if mid_val and mid_val in ["0", "1"]:
                        last_valid_idx = mid
                        left = mid + 1  # Continue searching for more recent valid values
                    else:
                        right = mid - 1
                
                if last_valid_idx >= 0:
                    prev_val = self.parser.query_cell(last_valid_idx, vcd_signal_name)

        for idx in range(start_idx, end_idx):
            t = times[idx]

            cur_val = self.parser.query_cell(idx, vcd_signal_name)
            if not cur_val:
                # Pin not present in this row
                continue

            # Only consider valid logic values for flip detection
            if cur_val not in ["0", "1"]:
                continue

            if prev_val is not None and cur_val != prev_val:
                is_rising = prev_val == "0" and cur_val == "1"
                is_falling = prev_val == "1" and cur_val == "0"
                if is_rising or is_falling:
                    events.append((is_rising, t))
            prev_val = cur_val

        return events
