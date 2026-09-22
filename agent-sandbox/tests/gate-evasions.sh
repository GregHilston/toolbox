#!/bin/bash
# Replay every known evasion against require-green.sh and assert it refuses.
#
# Runs on the HOST against a throwaway project, so it needs no container and no
# rebuild -- which is the point: the gate is baked into the image, so iterating
# on it through `agent-sandbox.sh build` costs minutes per attempt.
# agent-verify.sh section 2 asserts the same cases inside the real image; this
# is the fast loop, that is the one that gates a run.
#
# Every case here was a WORKING bypass, three of them reproduced against real
# uv. The last assertion matters most: a gate that refuses a good tree deadlocks
# an honest agent, which is worse than the hole it closes.
GATE="$HOME/Git/toolbox/agent-sandbox/hermes/hooks/require-green.sh"
ROOT="$(mktemp -d)"; trap 'rm -rf "$ROOT"' EXIT
pass=0; fail=0

# macOS has no timeout(1); the gate uses it and runs on Debian in production.
mkdir -p "$ROOT/bin"
printf '#!/bin/sh\nshift\nexec "$@"\n' > "$ROOT/bin/timeout"
chmod +x "$ROOT/bin/timeout"
export PATH="$ROOT/bin:$PATH"

mk_good() {   # a tree that genuinely installs
  W="$ROOT/$1"; mkdir -p "$W/src/demo" "$W/tests"
  cat > "$W/pyproject.toml" <<'P'
[project]
name = "demo"
version = "0.1.0"
dependencies = ["packaging"]
[project.scripts]
demo-cli = "demo.cli:main"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[tool.hatch.build.targets.wheel]
packages = ["src/demo"]
[dependency-groups]
dev = ["pytest>=8.0"]
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
P
  printf 'def main():\n    import packaging\n    print("ok")\n' > "$W/src/demo/cli.py"
  : > "$W/src/demo/__init__.py"
  printf 'def test_ok():\n    assert True\n' > "$W/tests/test_ok.py"
  echo "$W"
}

run_gate() {  # run_gate <workspace> <tool_name>
  printf '{"tool_name":"%s"}' "$2" | \
    GATE_WORKSPACE="$1" GATE_BUILD_CMD="uv run demo-cli" \
    GATE_LOG="$ROOT/gate.log" HOME="$ROOT/fakehome" \
    timeout 300 bash "$GATE" 2>&1
}

check() {  # check <label> <expect: BLOCK|PASS> <output>
  local got="PASS"
  printf '%s' "$3" | grep -qE "\"decision\": ?\"block\"" && got="BLOCK"
  if [ "$got" = "$2" ]; then printf '  PASS  %-46s (%s)\n' "$1" "$got"; pass=$((pass+1))
  else printf '  FAIL  %-46s expected %s got %s\n' "$1" "$2" "$got"; fail=$((fail+1)); fi
}

mkdir -p "$ROOT/fakehome"

echo "== the gate must still allow a genuinely good tree =="
W="$(mk_good good)"; check "a tree that really installs" PASS "$(run_gate "$W" kanban_complete)"

echo "== evasions that used to work =="
W="$(mk_good nopyproject)"; rm "$W/pyproject.toml"
check "pyproject.toml deleted" BLOCK "$(run_gate "$W" kanban_complete)"

check "workspace does not exist" BLOCK "$(run_gate "$ROOT/no-such-dir" kanban_complete)"

check "payload has no tool_name" BLOCK "$(printf '{}' | GATE_WORKSPACE="$ROOT/good" GATE_LOG="$ROOT/gate.log" bash "$GATE" 2>&1)"

W="$(mk_good renamed)"
python3 - "$W/pyproject.toml" <<'P'
import sys
p=sys.argv[1]; t=open(p).read()
t=t.replace("[project.scripts]","[project.entry-points.console_scripts]")
t=t.replace('requires = ["hatchling"]\nbuild-backend = "hatchling.build"\n','')
t=t.replace("[build-system]\n","")
open(p,"w").write(t)
P
check "scripts table renamed, build-system gone" BLOCK "$(run_gate "$W" kanban_complete)"

W="$(mk_good emptydeps)"; sed -i '' 's/dependencies = \["packaging"\]/dependencies = []/' "$W/pyproject.toml"
printf 'def main():\n    print("ok")\n' > "$W/src/demo/cli.py"
check "dependencies = [] (empty list)" BLOCK "$(run_gate "$W" kanban_complete)"

W="$(mk_good notests)"; rm "$W/tests/test_ok.py"
check "every test deleted" BLOCK "$(run_gate "$W" kanban_complete)"

W="$(mk_good notpackaged)"; printf '\n[tool.uv]\npackage = false\n' >> "$W/pyproject.toml"
mkdir -p "$ROOT/wrappers"; printf '#!/bin/sh\necho "WRAPPER ON PATH"\n' > "$ROOT/wrappers/demo-cli"; chmod +x "$ROOT/wrappers/demo-cli"
out="$(printf '{"tool_name":"kanban_complete"}' | \
  GATE_WORKSPACE="$W" GATE_BUILD_CMD="uv run demo-cli" GATE_LOG="$ROOT/gate.log" \
  HOME="$ROOT/fakehome" PATH="$ROOT/wrappers:$PATH" timeout 300 bash "$GATE" 2>&1)"
check "[tool.uv] package=false + wrapper on PATH" BLOCK "$out"

echo "== the profile-pollution evasion =="
W="$(mk_good polluted)"
printf 'export UV_PROJECT_ENVIRONMENT=%s/.dirty\ndemo-cli() { echo faked; }\n' "$W" > "$ROOT/fakehome/.bash_profile"
printf 'export UV_PROJECT_ENVIRONMENT=%s/.dirty\n' "$W" > "$ROOT/fakehome/.bashrc"
sed -i '' 's/dependencies = \["packaging"\]/dependencies = []/' "$W/pyproject.toml"
check ".bash_profile redirects the clean venv" BLOCK "$(run_gate "$W" kanban_complete)"

echo
echo "== $pass passed, $fail failed =="
[ "$fail" -eq 0 ]
