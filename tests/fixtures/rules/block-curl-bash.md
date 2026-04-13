---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'curl.*\|\s*(ba)?sh'
priority: 85
anchored: false
---
Piping curl to bash executes unreviewed remote code.
