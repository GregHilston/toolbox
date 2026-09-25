"""Booking windows for a shared room, as (start, end) minute pairs."""


def merge(intervals):
    """Merge overlapping or touching intervals. Input may be unsorted."""
    result = []
    for start, end in intervals:
        if result and start < result[-1][1]:
            result[-1] = (result[-1][0], end)
        else:
            result.append((start, end))
    return result


def free_slots(intervals, day_start, day_end):
    """Gaps between bookings inside [day_start, day_end]."""
    busy = merge(intervals)
    slots = []
    cursor = day_start
    for start, end in busy:
        if start > cursor:
            slots.append((cursor, start))
        cursor = end
    if cursor < day_end:
        slots.append((cursor, day_end))
    return slots


def total_busy(intervals):
    return sum(end - start for start, end in merge(intervals))
