---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: '\bsudo\b'
priority: 70
anchored: false
---
sudo is not allowed in automated tool calls.
