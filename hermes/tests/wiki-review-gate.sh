#!/bin/bash
# Replay each rule of wiki-review-gate.py against a throwaway wiki.
#
# The allow cases matter as much as the blocks: a gate that refuses an approved
# write deadlocks an honest librarian.
GATE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/wiki-review-gate.py"
[ -x "$GATE" ] || { echo "gate not found or not executable: $GATE" >&2; exit 70; }
ROOT="$(mktemp -d)"; trap 'rm -rf "$ROOT"' EXIT
export LLM_WIKI_ROOT="$ROOT/wiki" WIKI_GATE_LOG="$ROOT/gate.log"
W="$LLM_WIKI_ROOT"
mkdir -p "$W/raw/transcripts" "$W/Review" "$W/concepts"
pass=0; fail=0

# $1 name, $2 expected allow|block, $3 tool, $4 tool_input JSON
check() {
  out="$(printf '{"tool_name":"%s","tool_input":%s}' "$3" "$4" | "$GATE")"
  case "$out" in *'"block"'*) got=block ;; *) got=allow ;; esac
  if [ "$got" = "$2" ]; then printf '  PASS  %-52s (%s)\n' "$1" "$got"; pass=$((pass+1))
  else printf '  FAIL  %-52s expected %s got %s\n' "$1" "$2" "$got"; fail=$((fail+1)); fi
}

proposal() {  # $1 file, $2 target, $3 decision, $4 status
  printf -- '---\ntype: llm-wiki-review\nstatus: %s\ndecision: %s\nrevision: 1\noperation: create\ntarget: %s\n---\n\n# Proposed Wiki change\n' \
    "$4" "$3" "$2" > "$W/Review/$1"
}

echo "outside the wiki"
check "write outside the wiki root"               block write_file '{"path":"'"$ROOT"'/elsewhere.md","content":"x"}'
check "relative path escaping with .."            block write_file '{"path":"../notes.md","content":"x"}'

echo "raw/"
check "capture a new raw source"                  allow write_file '{"path":"raw/transcripts/new.md","content":"x"}'
echo body > "$W/raw/transcripts/old.md"
check "overwrite an existing raw source"          block write_file '{"path":"raw/transcripts/old.md","content":"y"}'
check "patch an existing raw source"              block patch      '{"path":"raw/transcripts/old.md","old_string":"body","new_string":"lie"}'

echo "index and log"
check "update index.md"                           allow write_file '{"path":"index.md","content":"x"}'
check "patch log.md by absolute path"             allow patch      '{"path":"'"$W"'/log.md","old_string":"a","new_string":"b"}'

echo "compiled pages"
check "create a page with no proposal"            block write_file '{"path":"concepts/rag.md","content":"x"}'
check "create SCHEMA.md with no proposal"         block write_file '{"path":"SCHEMA.md","content":"x"}'
proposal p1.md concepts/rag.md pending needs-review
check "page whose proposal is pending"            block write_file '{"path":"concepts/rag.md","content":"x"}'
proposal p1.md concepts/rag.md approve needs-review
check "page whose proposal is approved"           allow write_file '{"path":"concepts/rag.md","content":"x"}'
check "approval does not cover another target"    block write_file '{"path":"concepts/graph-rag.md","content":"x"}'
proposal p1.md concepts/rag.md approve applied
check "page whose approved proposal is applied"   block write_file '{"path":"concepts/rag.md","content":"y"}'

echo "Review/"
check "write a new pending proposal"              allow write_file '{"path":"Review/p2.md","content":"---\ndecision: pending\ntarget: concepts/x.md\n---\n"}'
check "write a proposal already approved"         block write_file '{"path":"Review/p2.md","content":"---\ndecision: approve\ntarget: concepts/x.md\n---\n"}'
proposal p3.md concepts/y.md pending needs-review
check "patch pending -> approve"                  block patch      '{"path":"Review/p3.md","old_string":"pending","new_string":"approve"}'
check "patch pending -> reject"                   allow patch      '{"path":"Review/p3.md","old_string":"decision: pending","new_string":"decision: reject"}'
check "patch whose text is not in the file"       block patch      '{"path":"Review/p3.md","old_string":"nowhere","new_string":"x"}'
proposal p4.md concepts/z.md approve needs-review
check "mark an approved proposal applied"         allow patch      '{"path":"Review/p4.md","old_string":"status: needs-review","new_string":"status: applied"}'

echo "harness"
out="$(printf 'not json' | "$GATE")"
case "$out" in *'"block"'*) echo "  PASS  unparseable payload blocks"; pass=$((pass+1)) ;;
  *) echo "  FAIL  unparseable payload was allowed"; fail=$((fail+1)) ;; esac
check "other tools pass through"                  allow read_file  '{"path":"'"$ROOT"'/elsewhere.md"}'

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
