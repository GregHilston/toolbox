"""opengym.py puts a plan file's routines into the app's state without the server."""

from __future__ import annotations

import unittest

from _loader import load

og = load("opengym.py")

LIB = {"0085": "barbell romanian deadlift", "4455": "45 degrees back extension", "0739": "sled 45° leg press"}


def state() -> dict:
    return {
        "unit": "lb",
        "routines": [
            {"id": "rb", "name": "Day B", "emoji": "x", "ex": [{"id": "0085", "sets": 3}, {"id": "c1", "sets": 2}]},
            {"id": "ra", "name": "Day A", "emoji": "y", "ex": [{"id": "0739"}]},
        ],
        "customEx": [{"id": "c1", "n": "Wall L-sit", "bp": "upper legs", "custom": True}],
    }


def plan(*routines: dict, custom: list | None = None) -> dict:
    return {"unit": "lb", "routines": list(routines), "customEx": custom or []}


class ApplyPlan(unittest.TestCase):
    def test_replaces_in_place_keeping_the_id(self):
        s = state()
        done = og.apply_plan(s, plan({"id": "r-b", "name": "Day B", "ex": [{"id": "4455", "sets": 3}]}), [], LIB)
        self.assertEqual(done, ["replaced Day B"])
        self.assertEqual(s["routines"][0], {"id": "rb", "name": "Day B", "emoji": None, "ex": [{"id": "4455", "sets": 3}]})
        self.assertEqual(s["routines"][1]["name"], "Day A")

    def test_maps_a_custom_exercise_to_the_apps_copy(self):
        s = state()
        wall = {"id": "gh-wall-lsit", "n": "wall l-sit", "bp": "upper legs"}
        og.apply_plan(s, plan({"name": "Day B", "ex": [{"id": "gh-wall-lsit"}]}, custom=[wall]), [], LIB)
        self.assertEqual(s["routines"][0]["ex"], [{"id": "c1"}])
        self.assertEqual(len(s["customEx"]), 1)

    def test_adds_a_new_custom_exercise_and_routine(self):
        s = state()
        new = {"id": "gh-x", "n": "New move", "bp": "back", "secondaries": ["lats"]}
        self.assertEqual(og.apply_plan(s, plan({"name": "Day C", "ex": [{"id": "gh-x"}]}, custom=[new]), [], LIB),
                         ["added Day C"])
        added = s["customEx"][-1]
        self.assertTrue(added["custom"])
        self.assertEqual(added["sm"], ["lats"])
        self.assertEqual(s["routines"][-1]["ex"], [{"id": added["id"]}])

    def test_only_named_routines(self):
        s = state()
        p = plan({"name": "Day B", "ex": [{"id": "4455"}]}, {"name": "Day A", "ex": [{"id": "4455"}]})
        self.assertEqual(og.apply_plan(s, p, ["Day A"], LIB), ["replaced Day A"])
        self.assertEqual(s["routines"][0]["ex"][0]["id"], "0085")

    def test_refuses_an_unknown_exercise_id(self):
        with self.assertRaises(SystemExit):
            og.apply_plan(state(), plan({"name": "Day B", "ex": [{"id": "9999999"}]}), [], LIB)

    def test_refuses_two_routines_of_one_name(self):
        s = state()
        s["routines"].append({"id": "rb2", "name": "Day B", "ex": []})
        with self.assertRaises(SystemExit):
            og.apply_plan(s, plan({"name": "Day B", "ex": []}), [], LIB)

    def test_refuses_a_different_unit(self):
        with self.assertRaises(SystemExit):
            og.apply_plan(state(), {**plan(), "unit": "kg"}, [], LIB)


class Dose(unittest.TestCase):
    def test_per_side_reps_are_half_the_total(self):
        self.assertEqual(og.dose({"sets": 2, "reps": 16, "side": True}), "2 x 8 per side")


if __name__ == "__main__":
    unittest.main()
