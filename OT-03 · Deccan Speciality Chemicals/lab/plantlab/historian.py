"""
Process historian (mock). Ten year retention, one second resolution.

It records values. It does not record who caused a value to change, which is
why F1 and F2 describe a plant behaviour and not an actor. Ten years of data
and it still cannot tell you who stopped the cooling.
"""

from __future__ import annotations

import csv
from datetime import datetime

from . import config as C
from .stores import Clock, ts

COLUMNS = [
    "ts", "R-201_pressure_bar", "R-201_temperature_C",
    "FIC-101_coolant_flow_pct", "FIC-101_setpoint_pct", "FIC-101_output_pct",
    "FIC-102_feed_flow_pct", "FV-102_valve_position_pct", "PRV_open",
]


class Historian:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.rows: list[dict] = []

    def record(self, snap: dict, loop_out: float, sp: float) -> None:
        self.rows.append({
            "ts": self.clock.now,
            "R-201_pressure_bar": snap["pressure"],
            "R-201_temperature_C": snap["temperature"],
            "FIC-101_coolant_flow_pct": snap["coolant_flow"],
            "FIC-101_setpoint_pct": sp,
            "FIC-101_output_pct": round(loop_out, 2),
            "FIC-102_feed_flow_pct": snap["feed_flow"],
            "FV-102_valve_position_pct": snap["feed_valve_position"],
            "PRV_open": int(snap["prv_open"]),
        })

    def export_csv(self, path: str) -> None:
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            for r in self.rows:
                row = dict(r)
                row["ts"] = ts(r["ts"])
                w.writerow(row)

    def slice(self, start: datetime, end: datetime) -> list[dict]:
        return [r for r in self.rows if start <= r["ts"] <= end]
