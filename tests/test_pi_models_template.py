"""pi's models.json template offers the LiteLLM gateway as home-lab defines it.

The aliases and the key reference are a contract with home-lab's gateway config,
and pi.nix reads this same file for rohan's models.json and the Ctrl+P cycle, so
a typo here breaks every host at once.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parent.parent / "dot" / "pi" / ".pi" / "agent" / "models.json.tpl"
)


class GatewayProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.providers = json.loads(TEMPLATE.read_text())["providers"]
        self.gateway = self.providers["litellm"]

    def test_is_listed_first(self) -> None:
        self.assertEqual(next(iter(self.providers)), "litellm")

    def test_endpoint_and_key(self) -> None:
        self.assertEqual(self.gateway["baseUrl"], "https://llm.grehg2.xyz/v1")
        self.assertEqual(self.gateway["apiKey"], "{{ op://Infra/LiteLLM/master_key }}")

    def test_offers_exactly_the_gateway_aliases(self) -> None:
        ids = [m["id"] for m in self.gateway["models"]]
        self.assertEqual(sorted(ids), ["cloud", "local-big", "local-lab", "local-small"])

    def test_local_aliases_fit_the_lab_profile(self) -> None:
        # Past 65536 the oMLX :lab profile rejects the prompt.
        for m in self.gateway["models"]:
            if m["id"] != "cloud":
                self.assertLessEqual(m["contextWindow"], 65536, m["id"])

    def test_only_cloud_costs_money(self) -> None:
        for m in self.gateway["models"]:
            paid = any(m["cost"].values())
            self.assertEqual(paid, m["id"] == "cloud", m["id"])

    def test_direct_omlx_provider_is_kept(self) -> None:
        self.assertEqual(self.providers["omlx"]["baseUrl"], "http://localhost:8000/v1")


if __name__ == "__main__":
    unittest.main()
