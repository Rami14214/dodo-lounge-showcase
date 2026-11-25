"""Pure availability engine: no DB, no web. Easy to test and to reason about."""
from datetime import date, datetime, time, timedelta

from .data import (CLOSE, CLOSED_WEEKDAYS, EARLIER_BY, EARLIEST, LAST_START, LUNCH, OPEN,
                   SERVICES, TZ, WEEKDAY_ONLY_STARTS, WEEKDAYS, is_fully_booked)

Window = tuple[datetime, datetime]


def booking_window(service_id: str, start: datetime) -> Window:
    return start, start + timedelta(minutes=SERVICES[service_id].minutes)


def is_open_day(day: date, now: datetime) -> bool:
    today = now.astimezone(TZ).date()
    return (day.weekday() not in CLOSED_WEEKDAYS and day >= today  # no upper limit: book years ahead
            and not is_fully_booked(day))


def _fixed(service_id: str, day: date) -> tuple[time, ...]:
    """The set start times for this day. Empty = back-to-back grid."""
    svc = SERVICES[service_id]
    if day.weekday() == 5 and svc.sat_starts is not None:
        return svc.sat_starts
    return svc.fixed_starts


def _candidates(service_id: str, day: date) -> list[time]:
    svc = SERVICES[service_id]
    cap = LAST_START.get(day.weekday())
    shift = timedelta(minutes=EARLIER_BY.get(day.weekday(), 0))
    floor = datetime.combine(day, EARLIEST, TZ)
    fixed = _fixed(service_id, day)
    if fixed:
        starts = [datetime.combine(day, t, TZ) for t in fixed]
        if svc.sat_starts is None and starts[0] - shift >= floor:  # Poly Gel already opens at 7:30
            starts = [s - shift for s in starts]
        return [s.time() for s in starts if cap is None or s.time() <= cap]
    out, t = [], max(datetime.combine(day, OPEN, TZ) - shift, floor)
    last = datetime.combine(day, CLOSE, TZ) - timedelta(minutes=svc.minutes)
    if cap is not None:
        last = min(last, datetime.combine(day, cap, TZ))
    while t <= last:
        out.append(t.time())
        t += timedelta(minutes=svc.minutes)  # back to back: next slot starts when this one ends
    return out


def _overlaps(a: Window, b: Window) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def lunch_ok(staff_id: str, day: date, busy: list[Window], new: Window) -> bool:
    """Mon-Fri, a staff member with LUNCH hours must keep at least one of them free."""
    hours = LUNCH.get(staff_id)
    if not hours or day.weekday() not in WEEKDAYS:
        return True
    taken = busy + [new]
    return any(not any(_overlaps((datetime.combine(day, a, TZ), datetime.combine(day, b, TZ)), w) for w in taken)
               for a, b in hours)


def available_starts(service_id: str, staff_id: str, day: date,
                     busy: list[Window], now: datetime) -> list[time]:
    """Start times for this service/staff/day that don't overlap `busy` (that staff's bookings)."""
    svc = SERVICES.get(service_id)
    if not svc or staff_id not in svc.staff or not is_open_day(day, now):
        return []
    if not _fixed(service_id, day):
        free = _packed_starts(service_id, day, busy, now)
    else:
        free = []
        for t in _candidates(service_id, day):
            w = booking_window(service_id, datetime.combine(day, t, TZ))
            if w[0] > now and not any(_overlaps(w, b) for b in busy):
                free.append(t)
    only = WEEKDAY_ONLY_STARTS.get(staff_id)
    if only and day.weekday() in WEEKDAYS:
        free = [t for t in free if t in only]
    return [t for t in free
            if lunch_ok(staff_id, day, busy, booking_window(service_id, datetime.combine(day, t, TZ)))]


def _packed_starts(service_id: str, day: date, busy: list[Window], now: datetime) -> list[time]:
    """Saturday pedicures: back-to-back slots, each one starts when the last one ends.
    If a slot hits an existing booking, the next slot starts right after that booking."""
    times = _candidates(service_id, day)
    if not times:
        return []
    step = timedelta(minutes=SERVICES[service_id].minutes)
    t = datetime.combine(day, times[0], TZ)
    last = datetime.combine(day, CLOSE, TZ) - step  # must end by closing time
    cap = LAST_START.get(day.weekday())
    if cap is not None:
        last = min(last, datetime.combine(day, cap, TZ))
    free = []
    while t <= last:
        end = t + step
        clash = [b_end for b_start, b_end in busy if t < b_end and b_start < end]
        if clash:
            t = max(clash)
            continue
        if t > now:
            free.append(t.time())
        t = end
    return free
