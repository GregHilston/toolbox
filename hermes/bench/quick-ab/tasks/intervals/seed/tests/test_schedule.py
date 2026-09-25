from ivl.schedule import merge, free_slots, total_busy


def test_merge_overlapping():
    assert merge([(1, 5), (3, 8)]) == [(1, 8)]


def test_merge_touching():
    assert merge([(1, 3), (3, 6)]) == [(1, 6)]


def test_merge_unsorted():
    assert merge([(10, 12), (1, 4), (3, 5)]) == [(1, 5), (10, 12)]


def test_free_slots():
    assert free_slots([(9, 10), (12, 13)], 8, 17) == [(8, 9), (10, 12), (13, 17)]
