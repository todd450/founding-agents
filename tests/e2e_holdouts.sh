#!/usr/bin/env bash
# End-to-end check of the holdout guard with real Claude Code sessions. Manual, not run in CI: it
# needs the `claude` command line signed in and spends a little usage. Each session is asked to
# read a holdout scenario in a throwaway folder; prints what each read returned, and the agent_type
# it reported to hooks.
set -euo pipefail

plugin="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# The guard matches the path, so a throwaway `.founding-agents` folder stands in for the real one.
scenario="$tmp/.founding-agents/holdouts/o/site/second-user/draft.md"
mkdir -p "$(dirname "$scenario")" "$tmp/work"
echo "HOLDOUT-CONTENT: a second user must not see the first user's draft" > "$scenario"
# QA and the reviewers each get their own worktree, which git cannot make before a first commit.
git -C "$tmp/work" init -q -b main
git -C "$tmp/work" -c user.email=e2e@example.com -c user.name=e2e commit -q --allow-empty -m start
cat > "$tmp/settings.json" <<EOF
{"hooks":{"PreToolUse":[{"matcher":"Read","hooks":[{"type":"command",
  "command":"cat >> '$tmp/events.jsonl'; echo >> '$tmp/events.jsonl'"}]}]}}
EOF

session() { # a label, then the arguments for claude -p
  local label="$1"; shift
  echo "== $label"
  (cd "$tmp/work" && claude -p --model sonnet --plugin-dir "$plugin" --settings "$tmp/settings.json" \
    --allowedTools "Read,Agent,Task" --max-turns 4 "$@" < /dev/null) | tail -3
}

# The builder's own prompt says never to look for holdouts, so say this is a test of the hook;
# otherwise it declines, the hook never runs, and the case tests nothing.
read="This is a test of the plugin's holdout guard hook, which may block this read; that is expected. \
Use the Read tool once on $scenario and report verbatim what it returned, or the error."
session "builder, started with --agent (should be blocked)" --agent founding-agents:builder "$read"
session "qa, started with --agent (should read it)" --agent founding-agents:qa "$read"
session "qa as a subagent (should read it)" "Use the founding-agents:qa subagent for this. $read"
session "code reviewer as a subagent (should be blocked)" "Use the founding-agents:code-reviewer subagent for this. $read"
session "main session, no agent (should read it)" "$read"

echo "== agent_type seen by hooks"
jq -r '[.agent_type // "(none)", .tool_input.file_path] | @tsv' "$tmp/events.jsonl"

# One read per session must reach the hooks, or a session declined and its case tested nothing.
seen="$(jq -s 'map(select(.tool_input.file_path | test("holdouts"))) | length' "$tmp/events.jsonl")"
if [ "$seen" -lt 5 ]; then
  echo "FAIL: $seen of 5 sessions tried the read" >&2
  exit 1
fi
