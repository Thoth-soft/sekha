---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'git\s+push.*--force'
priority: 80
anchored: false
---
Force-pushing rewrites shared history. Confirm explicitly.
