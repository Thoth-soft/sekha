---
severity: warn
triggers: [PreToolUse]
matches: [Bash]
pattern: 'git\s+reset\s+--hard'
priority: 50
anchored: false
---
git reset --hard discards uncommitted work.
