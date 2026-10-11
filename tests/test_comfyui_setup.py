"""comfyui-setup.sh against a scratch directory, with git, uv, curl and launchctl stubbed.

The script is the install and the upgrade path, run over a slow link, so the risks
are re-downloading gigabytes that are already there, giving up on a stalled file,
looping forever on a dead one, and overwriting Manager settings the user changed.
The curl stub serves each model as FAKE_SIZE bytes, FAKE_CHUNK at a time, so a
"stall" is a short read that the script must resume.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "comfyui-setup.sh"
MODELS = "\n".join([
    "diffusion_models https://example.test/m/klein.safetensors",
    "vae https://example.test/m/vae.safetensors",
])

STUBS = {
    "git": r'''
echo "git $*" >> "$CALLS"
case "$*" in
  *clone*) dir="${@: -1}"; mkdir -p "$dir/.git"; touch "$dir/requirements.txt" "$dir/manager_requirements.txt" ;;
esac
''',
    "uv": r'''
echo "uv $*" >> "$CALLS"
if [ "$1" = venv ]; then dir="${@: -1}"; mkdir -p "$dir/bin"; printf '#!/bin/sh\n' > "$dir/bin/python"; chmod +x "$dir/bin/python"; fi
''',
    "curl": r'''
out=""; head=0; url="${@: -1}"
while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift ;; -sfIL) head=1 ;; esac; shift; done
if [ "$head" = 1 ]; then printf 'HTTP/2 200\r\ncontent-length: %s\r\n' "$FAKE_SIZE"; exit 0; fi
echo "download $url" >> "$CALLS"
[ -n "${FAKE_FAIL:-}" ] && exit 22
have=$( [ -f "$out" ] && wc -c < "$out" || echo 0 )
n=$(( FAKE_SIZE - have )); [ "$n" -gt "$FAKE_CHUNK" ] && n=$FAKE_CHUNK
head -c "$n" /dev/zero >> "$out"
[ $(( have + n )) -ge "$FAKE_SIZE" ] || exit 28
''',
    "launchctl": r'''
echo "launchctl $*" >> "$CALLS"
[ "$1" = print ] && { [ -n "${FAKE_LOADED:-}" ] || exit 113; }
exit 0
''',
    "sleep": "exit 0",
}


class TestComfyuiSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        for name, body in STUBS.items():
            (stubs / name).write_text(f"#!/bin/bash\n{body}\n")
            (stubs / name).chmod(0o755)
        self.dir = self.tmp / "ComfyUI"
        self.calls = self.tmp / "calls"
        self.env = {
            "PATH": f"{stubs}:/usr/bin:/bin",
            "HOME": str(self.tmp),
            "COMFYUI_DIR": str(self.dir),
            "COMFYUI_MODELS": MODELS,
            "COMFYUI_FETCH_TRIES": "5",
            "CALLS": str(self.calls),
            "FAKE_SIZE": "1000",
            "FAKE_CHUNK": "1000",
        }

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_setup(self, **env):
        self.calls.write_text("")
        return subprocess.run(["/bin/bash", str(SCRIPT)], env={**self.env, **env},
                              capture_output=True, text=True, timeout=30)

    def calls_matching(self, prefix):
        return [c for c in self.calls.read_text().splitlines() if c.startswith(prefix)]

    def model(self, name):
        return self.dir / "models" / name

    def test_fresh_install_pins_torch_and_fetches_every_model(self):
        r = self.run_setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any("clone" in c for c in self.calls_matching("git")))
        install = next(c for c in self.calls_matching("uv pip install"))
        self.assertIn("torch==2.14.1", install)
        self.assertIn("torchvision==0.29.1", install)
        self.assertIn("manager_requirements.txt", install)
        for f in ("diffusion_models/klein.safetensors", "vae/vae.safetensors"):
            self.assertEqual(self.model(f).stat().st_size, 1000)
        ini = (self.dir / "user" / "__manager" / "config.ini").read_text()
        self.assertIn("use_uv = True", ini)
        self.assertIn("network_mode = personal_cloud", ini)
        self.assertIn("is not loaded", r.stdout)

    def test_rerun_fetches_nothing_keeps_manager_edits_and_restarts_the_agent(self):
        self.run_setup()
        ini = self.dir / "user" / "__manager" / "config.ini"
        ini.write_text("[default]\nuse_uv = True\nnetwork_mode = public\n")
        r = self.run_setup(FAKE_LOADED="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls_matching("download"), [])
        self.assertTrue(any("fetch" in c for c in self.calls_matching("git")))
        self.assertFalse(any("clone" in c for c in self.calls_matching("git")))
        self.assertIn("network_mode = public", ini.read_text())
        self.assertTrue(any("kickstart -k" in c for c in self.calls_matching("launchctl")))

    def test_a_stalled_download_resumes_until_complete(self):
        r = self.run_setup(FAKE_CHUNK="300")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.model("diffusion_models/klein.safetensors").stat().st_size, 1000)
        klein = [c for c in self.calls_matching("download") if "klein" in c]
        self.assertEqual(len(klein), 4)  # 300 + 300 + 300 + 100

    def test_a_dead_download_gives_up_and_fails(self):
        r = self.run_setup(FAKE_FAIL="1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("gave up on klein.safetensors after 5 tries", r.stderr)
        self.assertIn("gave up on vae.safetensors", r.stderr)  # one dead file does not stop the rest
        self.assertEqual(len(self.calls_matching("download")), 10)


if __name__ == "__main__":
    unittest.main()
