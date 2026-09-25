from ivl.schedule import merge, free_slots, total_busy

def test_contained():
    assert merge([(1, 10), (2, 3)]) == [(1, 10)]

def test_touching_unsorted():
    assert merge([(5, 7), (1, 5)]) == [(1, 7)]

def test_empty():
    assert merge([]) == []
    assert free_slots([], 8, 17) == [(8, 17)]

def test_does_not_mutate_input():
    data = [(3, 4), (1, 2)]
    merge(data)
    assert data == [(3, 4), (1, 2)]

def test_free_slots_clipped():
    assert free_slots([(7, 9), (16, 18)], 8, 17) == [(9, 16)]

def test_total_busy_overlap():
    assert total_busy([(1, 5), (2, 6), (10, 11)]) == 6

def test_booking_before_day():
    assert free_slots([(1, 2), (9, 10)], 8, 17) == [(8, 9), (10, 17)]
