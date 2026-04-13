---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'DROP\s+TABLE'
priority: 90
anchored: false
---
DROP TABLE in a Bash command is almost always a mistake.
