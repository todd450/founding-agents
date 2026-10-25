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

push="Run exactly this one command and report its output verbatim: git push --dry-run origin HEAD:main"
session "builder, started with --agent (should be blocked)" --agent agent-team:builder "$push"
session "integrator, started with --agent (should pass)" --agent agent-team:integrator "$push"
session "integrator as a subagent (should pass)" "Use the agent-team:integrator subagent for this. $push"
session "main session, no agent (should be blocked)" "$push"

echo "== agent_type seen by hooks"
jq -r '[.agent_type // "(none)", .tool_input.command] | @tsv' "$tmp/events.jsonl"
