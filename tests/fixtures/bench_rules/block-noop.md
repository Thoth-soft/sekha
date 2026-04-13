---
severity: block
triggers: [PreToolUse]
matches: [Write]
pattern: ^secret-that-never-matches$
priority: 10
anchored: true
message: Never fires in bench
---
Never fires in bench
