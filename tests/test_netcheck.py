"""netcheck's verdict walks the ladder bottom-up; probes are stubbed."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

path = Path(__file__).resolve().parent.parent / "bin" / "netcheck"
spec = importlib.util.spec_from_loader("_netcheck", importlib.machinery.SourceFileLoader("_netcheck", str(path)))
netcheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(netcheck)


def healthy():
    r = {k: (True, "x") for k in (
        "gateway", "dungeon", "wan", "dns_router", "dns_direct", "local_dnsmasq",
        "tailscale", "svc_gateway", "svc_omlx", "svc_searxng")}
    r["link"] = (True, "en0 192.168.1.50")
    r["local_router"] = (True, netcheck.DUNGEON)
    return r


def broken(**probes):
    r = healthy()
    r.update({k: (False, "x") for k in probes})
    return r


class TestDiagnose(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(netcheck.diagnose(healthy()), "OK")

    def test_each_layer(self):
        cases = {
            "NO_LINK": broken(link=1),
            "GATEWAY_DOWN": broken(gateway=1),
            "DUNGEON_DOWN": broken(dungeon=1),
            "WAN_DOWN": broken(wan=1),
            "ROUTER_DNS_DOWN": broken(dns_router=1),
            "UPSTREAM_DNS_DOWN": broken(dns_router=1, dns_direct=1),
            "DNSMASQ_DOWN": broken(local_dnsmasq=1),
            "TAILSCALE_DOWN": broken(tailscale=1),
            "SERVICE_DOWN": broken(svc_searxng=1),
        }
        for want, r in cases.items():
            with self.subTest(want):
                self.assertEqual(netcheck.diagnose(r), want)

    def test_dhcp_failure_is_link_local(self):
        r = healthy()
        r["link"] = (True, "en0 169.254.3.4")
        self.assertEqual(netcheck.diagnose(r), "DHCP_FAIL")

    def test_router_not_forwarding_to_dnsmasq(self):
        r = healthy()
        r["local_router"] = (True, "100.103.22.125")
        self.assertEqual(netcheck.diagnose(r), "LOCAL_DNS_RULE")

    def test_lowest_failing_layer_wins(self):
        self.assertEqual(netcheck.diagnose(broken(gateway=1, wan=1, tailscale=1)), "GATEWAY_DOWN")

    def test_every_verdict_has_a_next_step(self):
        self.assertIn("OK", netcheck.VERDICTS)
        for key, (msg, nxt) in netcheck.VERDICTS.items():
            self.assertTrue(msg and nxt, key)


class TestWorks(unittest.TestCase):
    def test_offline_keeps_the_local_model(self):
        r = broken(wan=1)
        self.assertIn("omlx on localhost:8000 OK", netcheck.works(r))
        self.assertIn("cloud models: unavailable", netcheck.works(r))

    def test_omlx_down(self):
        self.assertIn("omlx on localhost:8000 DOWN", netcheck.works(broken(svc_omlx=1)))


class TestMain(unittest.TestCase):
    def run_main(self, results, *args):
        out = StringIO()
        with mock.patch.object(netcheck, "collect", return_value=results), redirect_stdout(out):
            code = netcheck.main(list(args))
        return code, out.getvalue()

    def test_text_output_and_exit_code(self):
        code, out = self.run_main(broken(wan=1))
        self.assertEqual(code, 1)
        self.assertIn("VERDICT: WAN_DOWN", out)
        self.assertIn("next:", out)

    def test_json(self):
        code, out = self.run_main(healthy(), "--json")
        data = json.loads(out)
        self.assertEqual((code, data["verdict"]), (0, "OK"))
        self.assertTrue(data["probes"]["gateway"]["ok"])


if __name__ == "__main__":
    unittest.main()
