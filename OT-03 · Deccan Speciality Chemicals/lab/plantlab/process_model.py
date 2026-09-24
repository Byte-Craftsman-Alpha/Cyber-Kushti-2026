"""
The reactor and the mechanical relief valve (mock).

MODEL NOTE - read this before reading the numbers.
This is not a chemical kinetics model and it does not pretend to be one. It is
a four-line shape model, fitted so that the historian it feeds reproduces the
trace the investigation describes in F1:

    04:32   pressure still at normal operating pressure (about 8.1 bar)
    04:37   pressure crosses the 9.5 bar high pressure alarm set point
    04:41   pressure reaches the 12.0 bar relief valve set pressure
    04:41   relief valve lifts, discharges, reseats

The single state is `extent` (r): how far the reaction has run away, 0 to 1.
Pressure is a linear function of it. While the coolant is doing its job the
extent cannot grow. When the coolant is taken away the extent follows a
logistic curve, which is the standard "nothing, nothing, nothing, everything"
shape an exothermic runaway has.

Fitted constants
    EXTENT_PER_BAR   8.0 bar of pressure swing across the full extent
    T_MID            8,804 s after the coolant output was zeroed
    TAU              161 s  (width of the take-off)
Everything else in the class is bookkeeping.

FIDELITY NOTE on the operator's feed intervention.
The operator's own statement is that he began reducing feed and the relief
valve lifted before his action took effect, and F1 records the feed valve at
its commanded position throughout the rise. The lab therefore applies a dead
time to the operator's feed set point change. The dead time is a modelling
device to line the record up with F1. What the record actually means is
simply that whatever the operator did had not reached the valve by 04:41.
"""

from __future__ import annotations

import math
import random

from . import config as C

# --- fitted constants ------------------------------------------------------
EXTENT_PER_BAR = 8.0          # pressure swing across the full extent (bar)
T_MID = 8758.0                # seconds after the coolant was lost (04:40:00)
TAU = 161.2                   # seconds, logistic width
SEED = 1.0 / (1.0 + math.exp(T_MID / TAU))   # extent at the moment of loss
DISCHARGE_DECAY = 0.0035      # per second, heat removed while the valve is open
COOLING_DECAY_TAU = 240.0     # seconds, extent decay once cooling is restored
VALVE_STROKE = 20.0           # seconds for the coolant valve to travel fully
DEADBAND = 0.19               # bar, relief valve reseat hysteresis


class Reactor:
    def __init__(self, seed: int = 20270403):
        self.rng = random.Random(seed)

        self.extent = SEED            # reaction runaway extent
        self.pressure = C.P_NORMAL
        self.temperature = 138.0
        self.feed_flow = 45.0
        self.feed_valve_position = 45.0
        self.coolant_flow = 62.0
        self.coolant_valve_position = 62.0   # follows the controller output

        self.emergency_cooling = False   # set when XV-118 is opened by hand
        self.relief_open = False
        self.relief_seconds_open = 0.0
        self.relief_longest_discharge = 0.0
        self.relief_opened_at = None
        self.prv_lifts = 0
        self._discharging = False
        self.cooling_was_lost = False

    # ------------------------------------------------------------------

    def step(self, dt: float, coolant_pct: float, coolant_available: bool = True,
             manual_feed: float | None = None) -> dict:
        """
        coolant_pct        what the coolant flow controller commands, 0-100
        coolant_available  cooling actually reaching the jacket
        manual_feed        operator's manual feed set point, if any
        """
        # ---- the coolant valve follows the controller output ---------------
        target_valve = 0.0 if coolant_pct <= 0.01 else coolant_pct
        travel = dt / VALVE_STROKE * 100.0
        if abs(target_valve - self.coolant_valve_position) <= travel:
            self.coolant_valve_position = target_valve
        else:
            self.coolant_valve_position += math.copysign(travel,
                                                         target_valve - self.coolant_valve_position)
        cooling_on = (self.emergency_cooling
                      or (coolant_available and self.coolant_valve_position > 5.0))
        self.coolant_flow = round(self.coolant_valve_position, 2)

        if not cooling_on:
            self.cooling_was_lost = True

        # ---- reaction extent ----------------------------------------------
        # The runaway clock starts at the moment cooling is lost, not at the
        # moment the model happened to be switched on. That is what makes the
        # take-off land at the same wall clock time whatever time the
        # simulation was started.
        logistic = self.extent * (1.0 - self.extent) / TAU
        if cooling_on:
            if self.extent > SEED:
                # cooling pulls the accumulated heat away again
                self.extent -= self.extent / COOLING_DECAY_TAU * dt
            else:
                self.extent = SEED
            self.cooling_was_lost = False
        else:
            if not self.cooling_was_lost:
                self.cooling_was_lost = True
                self.extent = SEED          # the clock starts here
            self.extent += logistic * dt
            if self.relief_open:
                # venting removes enthalpy: the relief valve is what stops the run
                self.extent -= DISCHARGE_DECAY * self.extent * dt
        self.extent = min(max(self.extent, 0.0), 0.999)

        # ---- pressure ------------------------------------------------------
        underlying = C.P_NORMAL + EXTENT_PER_BAR * self.extent
        if self.relief_open:
            # while the valve is discharging it holds the vessel at its set
            # pressure. The gauge would not read above it.
            self.pressure = round(min(underlying, C.P_RELIEF + 0.01 * self.relief_seconds_open)
                                  + self.rng.uniform(-0.004, 0.004), 3)
        else:
            self.pressure = round(underlying + self.rng.uniform(-0.004, 0.004), 3)

        # temperature is derived: 8 degrees of reactor temperature per bar of
        # pressure swing, which keeps chemistry out of a security lab
        self.temperature = round(138.0 + (self.pressure - C.P_NORMAL) * 8.0, 1)

        # ---- feed ----------------------------------------------------------
        if manual_feed is not None:
            self.feed_flow = manual_feed
            self.feed_valve_position = manual_feed

        # ---- the mechanical relief valve: no electronics in it (F29) ------
        if not self.relief_open and underlying >= C.P_RELIEF:
            self.relief_open = True
            self.relief_seconds_open = 0.0
            self.prv_lifts += 1
        elif self.relief_open:
            self.relief_seconds_open += dt
            # reseats when the reaction itself has been knocked back far
            # enough for the vessel to sit a deadband below set pressure
            if underlying <= C.P_RELIEF - DEADBAND:
                self.relief_open = False
                self.relief_longest_discharge = max(self.relief_longest_discharge,
                                                    self.relief_seconds_open)

        return self.snapshot()

    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "pressure": round(self.pressure, 3),
            "temperature": self.temperature,
            "coolant_flow": self.coolant_flow,
            "feed_flow": self.feed_flow,
            "feed_valve_position": self.feed_valve_position,
            "extent": round(self.extent, 6),
            "prv_open": self.relief_open,
            "prv_seconds_open": round(self.relief_seconds_open, 1),
        }
