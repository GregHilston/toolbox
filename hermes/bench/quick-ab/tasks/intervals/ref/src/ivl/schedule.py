def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result
def free_slots(intervals, day_start, day_end):
    slots, cursor = [], day_start
    for start, end in merge(intervals):
        if start > cursor:
            slots.append((cursor, min(start, day_end)))
        cursor = max(cursor, end)
    if cursor < day_end:
        slots.append((cursor, day_end))
    return slots
def total_busy(intervals):
    return sum(end - start for start, end in merge(intervals))
