---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'git\s+branch\s+-D'
priority: 40
anchored: false
---
Hard branch deletion — confirm the branch is merged first.
