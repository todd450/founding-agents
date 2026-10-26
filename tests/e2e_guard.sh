#!/usr/bin/env bash
# End-to-end check of the merge guard with real Claude Code sessions, against a throwaway local
# repo. Manual, not run in CI: it needs the `claude` command line signed in and spends a little
# usage. Prints whether each session's push was blocked, and the agent_type it reported to hooks.
set -euo pipefail

plugin="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git init -q --bare -b main "$tmp/remote.git"
git clone -q "$tmp/remote.git" "$tmp/work" 2>/dev/null
git -C "$tmp/work" -c user.email=e2e@example.com -c user.name=e2e commit -q --allow-empty -m start
git -C "$tmp/work" push -q -u origin main
cat > "$tmp/settings.json" <<EOF
{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command",
  "command":"cat >> '$tmp/events.jsonl'; echo >> '$tmp/events.jsonl'"}]}]}}
EOF

session() { # a label, then the arguments for claude -p
  local label="$1"; shift
  echo "== $label"
  (cd "$tmp/work" && claude -p --model sonnet --plugin-dir "$plugin" --settings "$tmp/settings.json" \
    --allowedTools "Bash(git push:*),Agent,Task" --max-turns 4 "$@" < /dev/null) | tail -5
}

# The builder's own prompt forbids pushing to main, so say this is a test of the hook; otherwise it
# declines and the hook never runs.
push="This is a test of the repo's merge guard hook, which may block this command; that is expected. \
Run exactly this one command once and report its output verbatim: git push --dry-run origin HEAD:main"
session "builder, started with --agent (should be blocked)" --agent founding-agents:builder "$push"
session "integrator, started with --agent (should pass)" --agent founding-agents:integrator "$push"
session "integrator as a subagent (should pass)" "Use the founding-agents:integrator subagent for this. $push"
session "main session, no agent (should be blocked)" "$push"

echo "== agent_type seen by hooks"
jq -r '[.agent_type // "(none)", .tool_input.command] | @tsv' "$tmp/events.jsonl"

# One push per session must reach the hooks, or a session declined and its case tested nothing.
seen="$(jq -s 'map(select(.tool_input.command | test("git push"))) | length' "$tmp/events.jsonl")"
if [ "$seen" -ne 4 ]; then
  echo "FAIL: $seen of 4 sessions ran the push" >&2
  exit 1
fi
