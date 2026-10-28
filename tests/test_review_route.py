"""review-route.py sends logic to DeepSeek, UI to Sonnet and test-only branches to nobody."""

from __future__ import annotations

import unittest

from _loader import load

rr = load("review-route.py")


class Route(unittest.TestCase):
    def test_each_route(self) -> None:
        cases = {
            "none": ["api-backend/tests/test_a.py", "data.jsonc", "docs/x.md"],
            "sonnet": ["api-backend/src/a.py", "godot-client/shell/hud/hud.gd"],
            "deepseek": ["api-backend/src/a.py", "api-backend/tests/test_a.py"],
        }
        for want, files in cases.items():
            self.assertEqual(rr.route(files), want, files)

    def test_a_scene_or_image_needs_sonnet(self) -> None:
        for f in ("godot-client/main.tscn", "art/x.png", "web/app.css"):
            self.assertEqual(rr.route(["src/a.py", f]), "sonnet", f)


if __name__ == "__main__":
    unittest.main()
