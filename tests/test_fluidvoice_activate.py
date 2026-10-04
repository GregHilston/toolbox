"""fluidvoice-activate.sh against a scratch defaults domain, never FluidVoice's own.

The script owns FluidVoice's model routing on every deploy, so the risks are writing
something wrong, quitting the app when nothing changed, and wiping a key when a
step fails. pgrep, osascript and pkill are stubbed: FV_RUNNING is the app's pid
file, and FV_WEDGED makes it ignore quit and SIGTERM.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "nixos" / "modules" / "darwin" / "fluidvoice-activate.sh"
JQ = shutil.which("jq")
BASE_URL = "http://localhost:8000/v1"
PROVIDER = {"id": "omlx", "baseURL": BASE_URL, "models": ["Qwen3.6-35B-A3B-4bit", "Qwen3.6-35B-A3B-4bit:lab"]}
STRINGS = "\n".join([
    "SelectedProviderID=fluid-1",
    "SelectedDictationPromptID=__FLUID_1__",
    "RewriteModeSelectedProviderID=omlx",
    "RewriteModeSelectedModel=Qwen3.6-35B-A3B-4bit:lab",
    "CommandModeSelectedProviderID=omlx",
    "CommandModeSelectedModel=Qwen3.6-35B-A3B-4bit",
])
DICTIONARY = [{"triggers": ["quinn"], "replacement": "Qwen"}, {"triggers": ["o mlx"], "replacement": "oMLX"}]

STUBS = {
    "pgrep": '[ -f "$FV_RUNNING" ]',
    "osascript": 'echo osascript >> "$FV_CALLS"; [ -n "${FV_WEDGED:-}" ] || rm -f "$FV_RUNNING"',
    "pkill": 'echo pkill >> "$FV_CALLS"; [ -n "${FV_WEDGED:-}" ] || rm -f "$FV_RUNNING"',
}


@unittest.skipUnless(JQ and shutil.which("defaults"), "needs macOS defaults and jq")
class TestFluidVoiceActivate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.domain = f"com.example.fluidvoice-test-{uuid.uuid4().hex[:8]}"
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        for name, body in STUBS.items():
            (stubs / name).write_text(f"#!/bin/sh\n{body}\n")
            (stubs / name).chmod(0o755)
        (self.tmp / "launch").write_text("#!/bin/sh\necho LAUNCHED\n")
        (self.tmp / "launch").chmod(0o755)
        (self.tmp / "FluidVoice.app").mkdir()
        (self.tmp / "settings.json").write_text(json.dumps({"auth": {"api_key": "k"}}))
        self.calls = self.tmp / "calls"
        self.running = self.tmp / "running"
        self.env = {
            "PATH": f"{stubs}:{Path(JQ).parent}:/usr/bin:/bin:/usr/sbin",
            "HOME": os.environ["HOME"],
            "DOMAIN": self.domain,
            "APP": str(self.tmp / "FluidVoice.app"),
            "HANDY_STORE": str(self.tmp / "no-handy.json"),
            "OMLX_SETTINGS": str(self.tmp / "settings.json"),
            "SEED_DICTATION": "[]",
            "SEED_DICTATION_LEGACY": "{}",
            "SEED_COMMAND": "{}",
            "SEED_WRITE": "{}",
            "DICTIONARY": json.dumps(DICTIONARY),
            "PROVIDER": json.dumps(PROVIDER),
            "STRINGS": STRINGS,
            "LAUNCH": str(self.tmp / "launch"),
            "QUIT_POLL": "0",
            "FV_RUNNING": str(self.running),
            "FV_CALLS": str(self.calls),
        }

    def tearDown(self):
        subprocess.run(["defaults", "delete", self.domain], capture_output=True)
        shutil.rmtree(self.tmp)

    # helpers

    def run_script(self, **extra) -> subprocess.CompletedProcess:
        self.calls.unlink(missing_ok=True)
        return subprocess.run(["/bin/bash", str(SCRIPT)], env={**self.env, **extra},
                              capture_output=True, text=True, timeout=60)

    def read(self, key: str) -> str | None:
        r = subprocess.run(["defaults", "read", self.domain, key], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    def read_data(self, key: str):
        exported = subprocess.run(["defaults", "export", self.domain, "-"], capture_output=True, check=True).stdout
        raw = subprocess.run(["plutil", "-extract", key, "raw", "-o", "-", "-"], input=exported, capture_output=True)
        if raw.returncode:
            return None
        return json.loads(subprocess.run(["base64", "-d"], input=raw.stdout, capture_output=True).stdout)

    def write_data(self, key: str, value) -> None:
        blob = value if isinstance(value, bytes) else json.dumps(value).encode()
        subprocess.run(["defaults", "write", self.domain, key, "-data", blob.hex()], check=True)

    def onboarded(self) -> None:
        """A seeded, onboarded install: the state managed settings apply to."""
        self.run_script()
        subprocess.run(["defaults", "write", self.domain, "OnboardingCompleted", "-bool", "true"], check=True)

    def scrub_key(self) -> None:
        """What the app does at launch: move apiKey to its Keychain."""
        self.write_data("SavedProviders", [{**p, "apiKey": ""} for p in self.read_data("SavedProviders")])

    def quits(self) -> bool:
        return self.calls.exists() and "osascript" in self.calls.read_text()

    # tests

    def test_fresh_install_seeds_and_leaves_onboarding_alone(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNotNone(self.read_data("PrimaryDictationShortcuts"))
        self.assertIn("onboarding unfinished", r.stdout)
        self.assertIsNone(self.read("SelectedProviderID"))
        self.assertIn("LAUNCHED", r.stdout)

    def test_applies_routing_provider_and_fingerprint(self):
        self.onboarded()
        r = self.run_script()
        self.assertIn("applying managed settings", r.stdout)
        self.assertEqual(self.read("SelectedProviderID"), "fluid-1")
        self.assertEqual(self.read("SelectedDictationPromptID"), "__FLUID_1__")
        self.assertEqual(self.read("RewriteModeSelectedModel"), "Qwen3.6-35B-A3B-4bit:lab")
        self.assertEqual(self.read("RewriteModeLinkedToGlobal"), "0")
        self.assertEqual(self.read("CommandModeLinkedToGlobal"), "0")
        [omlx] = self.read_data("SavedProviders")
        self.assertEqual((omlx["id"], omlx["apiKey"], omlx["name"]), ("omlx", "k", "oMLX"))
        want = hashlib.sha256(f"{BASE_URL}|k".encode()).hexdigest()
        self.assertEqual(self.read_data("VerifiedProviderFingerprints"), {"custom:omlx": want})

    def test_no_drift_after_the_app_moves_the_key(self):
        self.onboarded()
        self.run_script()
        self.scrub_key()
        self.running.touch()
        r = self.run_script()
        self.assertNotIn("applying", r.stdout)
        self.assertFalse(self.quits(), "quit the app with nothing to change")

    def test_a_provider_added_in_the_app_is_kept_without_drift(self):
        self.onboarded()
        self.run_script()
        self.scrub_key()
        mine = {"id": "zzz", "name": "Other", "baseURL": "http://example:1/v1", "apiKey": "", "models": []}
        self.write_data("SavedProviders", self.read_data("SavedProviders") + [mine])
        r = self.run_script()
        self.assertNotIn("applying", r.stdout)
        self.assertIn("zzz", [p["id"] for p in self.read_data("SavedProviders")])

    def test_old_provider_at_the_same_url_is_replaced(self):
        self.onboarded()
        self.write_data("SavedProviders", [{"id": "UUID-1", "name": "omlx", "baseURL": BASE_URL, "apiKey": "", "models": []}])
        self.run_script()
        self.assertEqual([p["id"] for p in self.read_data("SavedProviders")], ["omlx"])

    def test_default_prompt_model_override_is_blanked(self):
        self.onboarded()
        self.write_data("DictationPromptConfigurations", {"__default__": {"providerID": "UUID-1", "modelName": "Qwen"}})
        self.run_script()
        self.assertEqual(self.read_data("DictationPromptConfigurations"),
                         {"__default__": {"providerID": "", "modelName": ""}})

    def test_a_wedged_app_writes_nothing_and_the_rest_still_runs(self):
        self.onboarded()
        self.running.touch()
        r = self.run_script(FV_WEDGED="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("did not quit", r.stderr)
        self.assertIn("managed settings skipped", r.stderr)
        self.assertIn("pkill", self.calls.read_text(), "never escalated to SIGTERM")
        self.assertIsNone(self.read("SelectedProviderID"))
        self.assertIn("LAUNCHED", r.stdout)

    def test_unreadable_providers_are_left_alone(self):
        self.onboarded()
        self.write_data("SavedProviders", b"not json")
        r = self.run_script()
        self.assertIn("managed settings skipped", r.stderr)
        exported = subprocess.run(["defaults", "export", self.domain, "-"], capture_output=True, check=True).stdout
        raw = subprocess.run(["plutil", "-extract", "SavedProviders", "raw", "-o", "-", "-"], input=exported, capture_output=True)
        self.assertEqual(subprocess.run(["base64", "-d"], input=raw.stdout, capture_output=True).stdout, b"not json")

    def test_no_key_still_routes_but_skips_the_fingerprint(self):
        self.onboarded()
        (self.tmp / "settings.json").write_text("{}")
        r = self.run_script()
        self.assertIn("no oMLX key", r.stderr)
        self.assertEqual(self.read("SelectedProviderID"), "fluid-1")
        self.assertIsNone(self.read_data("VerifiedProviderFingerprints"))

    def test_dictionary_is_add_only(self):
        self.write_data("CustomDictionaryEntries", [{"id": "KEEP", "triggers": ["kwen"], "replacement": "Qwen"}])
        self.run_script()
        entries = self.read_data("CustomDictionaryEntries")
        self.assertEqual([(e["replacement"], e["id"] == "KEEP") for e in entries], [("Qwen", True), ("oMLX", False)])
        r = self.run_script()
        self.assertNotIn("adding Custom Dictionary", r.stdout)


if __name__ == "__main__":
    unittest.main()
