"""
Log stores that behave the way the real ones behaved.

Three behaviours matter to this case and each is modelled explicitly:

  * RingLog          - fixed number of events, oldest overwritten (F31)
  * TimedStore       - fixed retention in days, purged on write (F5, F7, F25)
  * CurrentStateOnly - keeps no history at all (F16, the suppression list)

A Clock object supplies the simulated wall clock so every store timestamps
consistently with the scenario.
"""

from __future__ import annotations

from datetime import datetime, timedelta


class Clock:
    """Simulated wall clock. Nothing in the lab reads the real system time."""

    def __init__(self, start: datetime):
        self.now = start
        self.start = start

    def set(self, when: datetime) -> None:
        if when < self.now:
            raise ValueError("clock does not run backwards")
        self.now = when

    def rewind_to(self, when: datetime) -> None:
        """Only for building the model's past. Never used inside a run."""
        self.now = when

    def advance(self, seconds: float, on_tick=None, tick_seconds: float = 1.0) -> None:
        """Advance the clock in fixed steps, calling on_tick each step."""
        remaining = float(seconds)
        while remaining > 1e-9:
            step = min(tick_seconds, remaining)
            self.now = self.now + timedelta(seconds=step)
            if on_tick is not None:
                on_tick(step)
            remaining -= step

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Clock {self.now:%Y-%m-%d %H:%M:%S}>"


def ts(when: datetime) -> str:
    return when.strftime("%Y-%m-%d %H:%M:%S")


class RingLog:
    """Fixed-size event log. When it is full the oldest entry is dropped."""

    def __init__(self, name: str, capacity: int, clock: Clock):
        self.name = name
        self.capacity = capacity
        self.clock = clock
        self._events: list[dict] = []
        self.overwritten = 0

    def write(self, kind: str, detail: str = "", actor: str = "", source: str = "") -> dict:
        return self.write_at(self.clock.now, kind, detail, actor, source)

    def write_at(self, when, kind: str, detail: str = "", actor: str = "",
                 source: str = "") -> dict:
        """Write with an explicit timestamp, used when backfilling history."""
        event = {
            "ts": when,
            "kind": kind,
            "detail": detail,
            "actor": actor,
            "source": source,
        }
        if self._events and when < self._events[-1]["ts"]:
            raise ValueError("ring log backfill must run in time order")
        self._events.append(event)
        while len(self._events) > self.capacity:
            self._events.pop(0)
            self.overwritten += 1
        return event

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    def window(self) -> tuple[datetime, datetime] | None:
        if not self._events:
            return None
        return self._events[0]["ts"], self._events[-1]["ts"]

    def find(self, kind: str | None = None, contains: str | None = None) -> list[dict]:
        out = []
        for e in self._events:
            if kind and e["kind"] != kind:
                continue
            if contains and contains.lower() not in (e["detail"] + e["actor"]).lower():
                continue
            out.append(e)
        return out


class TimedStore:
    """Log with a retention period in days. Old entries are purged on write."""

    def __init__(self, name: str, retention_days: int, clock: Clock):
        self.name = name
        self.retention_days = retention_days
        self.clock = clock
        self.rows: list[dict] = []
        self.purged = 0
        # Purging on every single write is O(n^2) across a busy log and buys
        # nothing at day-granularity retention, so it runs at most hourly.
        self._last_purge = clock.now

    def write(self, **fields) -> dict:
        row = {"ts": self.clock.now}
        row.update(fields)
        self.rows.append(row)
        if self.clock.now - self._last_purge > timedelta(hours=1):
            self._purge()
        return row

    def _purge(self) -> None:
        if self.retention_days <= 0:
            return
        self._last_purge = self.clock.now
        cutoff = self.clock.now - timedelta(days=self.retention_days)
        keep = [r for r in self.rows if r["ts"] >= cutoff]
        self.purged += len(self.rows) - len(keep)
        self.rows = keep

    def window(self) -> tuple[datetime, datetime] | None:
        if not self.rows:
            return None
        return self.rows[0]["ts"], self.rows[-1]["ts"]

    def query(self, **match) -> list[dict]:
        out = []
        for r in self.rows:
            if all(r.get(k) == v for k, v in match.items()):
                out.append(r)
        return out


class CurrentStateOnly:
    """Keeps the present and forgets the past. Models the suppression list (F16)."""

    def __init__(self, name: str):
        self.name = name
        self.state: dict[str, dict] = {}
        self.writes = 0

    def set(self, key: str, value: dict) -> None:
        self.state[key] = dict(value)
        self.writes += 1

    def clear(self, key: str) -> None:
        self.state.pop(key, None)

    def get(self, key: str) -> dict | None:
        return self.state.get(key)

    def keys(self) -> list[str]:
        return sorted(self.state)

    def history(self) -> list:
        return []  # by design there is none
