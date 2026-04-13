---
severity: block
triggers: [PreToolUse]
matches: [Bash]
pattern: 'eval\s+"'
priority: 60
anchored: false
---
eval of arbitrary strings is a footgun.
